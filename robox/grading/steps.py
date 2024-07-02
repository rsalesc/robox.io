import pathlib
import shlex
import subprocess
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel
from rich.text import Text

from robox import utils
from robox.config import get_bits_stdcpp, get_jngen, get_testlib
from robox.console import console
from robox.grading.judge.sandbox import SandboxBase, SandboxParams
from robox.grading.judge.storage import copyfileobj

MAX_STDOUT_LEN = 1024 * 1024 * 128  # 128 MB


class Outcome(Enum):
    ACCEPTED = 'accepted'
    WRONG_ANSWER = 'wrong-answer'
    JUDGE_FAILED = 'judge-failed'
    RUNTIME_ERROR = 'runtime-error'
    TIME_LIMIT_EXCEEDED = 'time-limit-exceeded'
    MEMORY_LIMIT_EXCEEDED = 'memory-limit-exceeded'
    OUTPUT_LIMIT_EXCEEDED = 'output-limit-exceeded'
    INTERNAL_ERROR = 'internal-error'


class DigestHolder(BaseModel):
    value: Optional[str] = None


class GradingLogsHolder(BaseModel):
    run: Optional['RunLog'] = None


class DigestOrSource(BaseModel):
    # Source path relative to the FS.
    src: Optional[pathlib.Path] = None
    # Digest if we should get file from storage.
    digest: Optional[DigestHolder] = None

    @staticmethod
    def create(data: Union[pathlib.Path, DigestHolder, str]) -> 'DigestOrSource':
        if isinstance(data, str):
            return DigestOrSource(digest=DigestHolder(value=data))
        if isinstance(data, DigestHolder):
            return DigestOrSource(digest=data)
        return DigestOrSource(src=data)

    def expand(self) -> Dict[str, Any]:
        res = {}
        if self.src is not None:
            res['src'] = self.src
        if self.digest is not None:
            res['digest'] = self.digest
        return res


class DigestOrDest(BaseModel):
    # Destination path relative to the FS.
    dest: Optional[pathlib.Path] = None
    # Digest if we should get file from storage.
    digest: Optional[DigestHolder] = None

    @staticmethod
    def create(data: Union[pathlib.Path, DigestHolder, str]) -> 'DigestOrDest':
        if isinstance(data, str):
            return DigestOrDest(digest=DigestHolder(value=data))
        if isinstance(data, DigestHolder):
            return DigestOrDest(digest=data)
        return DigestOrDest(dest=data)

    def expand(self) -> Dict[str, Any]:
        res = {}
        if self.dest is not None:
            res['dest'] = self.dest
        if self.digest is not None:
            res['digest'] = self.digest
        return res


class GradingFileInput(BaseModel):
    # Destination path relative to the sandboox.
    dest: pathlib.Path
    # Source path relative to the FS.
    src: Optional[pathlib.Path] = None
    # Digest if we should get file from storage.
    digest: Optional[DigestHolder] = None
    # Whether the destination file should be marked as an executable.
    executable: bool = False


class GradingFileOutput(BaseModel):
    # Source path relative to the sandbox.
    src: pathlib.Path
    # Destination path relative to the FS.
    dest: Optional[pathlib.Path] = None
    # Digest if we should put file in storage.
    digest: Optional[DigestHolder] = None
    # Whether the destination file should be marked as an executable.
    executable: bool = False
    # Whether the file is optional or not.
    optional: bool = False
    # Whether to cap its size
    maxlen: Optional[int] = None
    # Whether the file is just an intermediate file that should not be tracked.
    intermediate: bool = False


class GradingArtifacts(BaseModel):
    # Root directory for the produced artifacts.
    root: pathlib.Path = pathlib.PosixPath('.')
    # List of input files to copy to the sandbox.
    inputs: List[GradingFileInput] = []
    # List of output files to copy from the sandbox.
    outputs: List[GradingFileOutput] = []
    # Capture certain logs of the execution.
    logs: Optional[GradingLogsHolder] = None


class TestcaseIO(BaseModel):
    index: int
    input: Optional[pathlib.Path] = None
    output: Optional[pathlib.Path] = None


class PreprocessLog(BaseModel):
    cmd: List[str]
    exitcode: int
    log: str


class RunLog(BaseModel):
    exitcode: int = 0
    exitstatus: str = SandboxBase.EXIT_SANDBOX_ERROR
    time: Optional[float] = 0.0


class TestcaseLog(RunLog):
    stdout_absolute_path: Optional[pathlib.Path] = None
    stderr_absolute_path: Optional[pathlib.Path] = None
    log_absolute_path: Optional[pathlib.Path] = None


class CheckerResult(BaseModel):
    outcome: Outcome
    message: str = ''
    no_tle_outcome: Optional[Outcome] = None


class Evaluation(BaseModel):
    result: CheckerResult
    testcase: TestcaseIO
    log: TestcaseLog


def _process_input_artifacts(artifacts: GradingArtifacts, sandbox: SandboxBase):
    for input_artifact in artifacts.inputs:
        if input_artifact.digest is not None:
            assert input_artifact.digest.value is not None
            sandbox.create_file_from_storage(
                input_artifact.dest,
                input_artifact.digest.value,
                override=True,
                executable=input_artifact.executable,
            )
            continue
        assert input_artifact.src is not None
        sandbox.create_file_from_bytes(
            input_artifact.dest,
            (artifacts.root / input_artifact.src).read_bytes(),
            executable=input_artifact.executable,
            override=True,
        )


def _process_output_artifacts(
    artifacts: GradingArtifacts, sandbox: SandboxBase
) -> bool:
    for output_artifact in artifacts.outputs:
        if not sandbox.file_exists(output_artifact.src):
            if output_artifact.optional:
                continue
            console.print(
                f'[error]Output artifact [item]{output_artifact.src}[/item] does not exist.[/error]'
            )
            return False
        if output_artifact.digest is not None:
            output_artifact.digest.value = sandbox.get_file_to_storage(
                output_artifact.src,
                trunc_len=output_artifact.maxlen,
            )
            continue
        assert output_artifact.dest
        dst: pathlib.Path = artifacts.root / output_artifact.dest
        # Ensure dst directory exists.
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open('wb') as f:
            with sandbox.get_file(output_artifact.src) as sb_f:
                copyfileobj(
                    sb_f,
                    f,
                    maxlen=output_artifact.maxlen,
                )
        if output_artifact.executable:
            dst.chmod(0o755)
    return True


def testlib_grading_input() -> GradingFileInput:
    return GradingFileInput(src=get_testlib(), dest=pathlib.Path('testlib.h'))


def jngen_grading_input() -> GradingFileInput:
    return GradingFileInput(src=get_jngen(), dest=pathlib.Path('jngen.h'))


def _is_cpp_command(exe_command: str) -> bool:
    return exe_command.endswith('g++') or exe_command.endswith('clang++')


def _maybe_get_bits_stdcpp_for_clang(command: str) -> Optional[GradingFileInput]:
    cmds = shlex.split(command)
    if not cmds:
        return None
    exe = cmds[0]

    if not _is_cpp_command(exe):
        return None

    output = subprocess.run([exe, '-v'], capture_output=True)
    if output.returncode != 0:
        console.print('[error]Failed to get g++/clang compiler version.[/error]')
        return None
    lines = output.stderr.decode().splitlines()
    if not lines:
        return None
    # Check the first line for `clang`.
    if 'clang' not in lines[0]:
        return None

    bits = get_bits_stdcpp()
    return GradingFileInput(src=bits, dest=pathlib.Path('bits/stdc++.h'))


def _maybe_get_bits_stdcpp_for_commands(
    commands: List[str],
) -> Optional[GradingFileInput]:
    for command in commands:
        res = _maybe_get_bits_stdcpp_for_clang(command)
        if res is not None:
            return res
    return None


def compile(
    commands: List[str],
    params: SandboxParams,
    sandbox: SandboxBase,
    artifacts: GradingArtifacts,
) -> bool:
    bits_artifact = _maybe_get_bits_stdcpp_for_commands(commands)
    if bits_artifact is not None:
        _process_input_artifacts(GradingArtifacts(inputs=[bits_artifact]), sandbox)
    _process_input_artifacts(artifacts, sandbox)

    if not commands:
        # Code does not need preprocessing of any kind.
        return True

    logs: List[PreprocessLog] = []
    sandbox.set_params(params)

    for i, command in enumerate(commands):
        cmd = shlex.split(command)
        stdout_file = pathlib.PosixPath(f'compile-{i}.stdout')
        stderr_file = pathlib.PosixPath(f'compile-{i}.stderr')
        sandbox.params.set_stdall(stdout=stdout_file, stderr=stderr_file)

        if bits_artifact is not None and _is_cpp_command(cmd[0]):
            # Include from sandbox directory to import bits/stdc++.h.
            cmd.append('-I.')

        if not sandbox.execute_without_std(cmd, wait=True):
            console.print(
                '[error]Sandbox crashed while processing command:[/error]',
                utils.highlight_json_obj(cmd),
            )
            return False

        std_outputs = [
            sandbox.get_file_to_string(stderr_file, maxlen=None)
            if sandbox.file_exists(stderr_file)
            else '<No stderr produced by command>',
            sandbox.get_file_to_string(stdout_file, maxlen=None)
            if sandbox.file_exists(stdout_file)
            else '<No stdout produced by command>',
        ]

        log = PreprocessLog(
            cmd=cmd,
            exitcode=sandbox.get_exit_code(),
            log='\n'.join(std_outputs),
        )
        logs.append(log)

        if log.exitcode != 0:
            break

    if logs and logs[-1].exitcode != 0:
        console.print(
            'Preprocessing [error]failed[/error] with command',
            utils.highlight_json_obj(logs[-1].cmd),
        )
        console.print(f'Exit code: [error]{logs[-1].exitcode}[/error]')
        console.print(Text.from_ansi(logs[-1].log), style='default')
        return False

    return _process_output_artifacts(artifacts, sandbox)


def run(
    command: str,
    params: SandboxParams,
    sandbox: SandboxBase,
    artifacts: GradingArtifacts,
) -> Optional[RunLog]:
    _process_input_artifacts(artifacts, sandbox)
    cmd = shlex.split(command)
    sandbox.set_params(params)

    if not sandbox.execute_without_std(cmd, wait=True):
        console.print(
            '[error]Sandbox crashed while processing command:[/error]',
            utils.highlight_json_obj(cmd),
        )
        return None

    if not _process_output_artifacts(artifacts, sandbox):
        return None

    run_log = RunLog(
        exitcode=sandbox.get_exit_code(),
        exitstatus=sandbox.get_exit_status(),
        time=sandbox.get_execution_time(),
    )
    if artifacts.logs is not None:
        artifacts.logs.run = run_log.model_copy()
    return run_log


def _normalize_checked_words(s: str) -> Tuple[str, ...]:
    return tuple(s.split())


def _wcmp_check(expected: str, output: str) -> Outcome:
    if _normalize_checked_words(expected) == _normalize_checked_words(output):
        return Outcome.ACCEPTED

    return Outcome.WRONG_ANSWER


def get_checker_sandbox_params() -> SandboxParams:
    params = SandboxParams(
        max_processes=None,
        preserve_env=True,
    )
    params.add_mapped_directory(pathlib.Path('/usr'))
    params.add_mapped_directory(pathlib.Path('/etc'))
    return params


def _check(
    sandbox: SandboxBase,
    testcase: TestcaseIO,
    output_path: pathlib.Path,
    should_use_python_checker: bool = False,
) -> CheckerResult:
    if testcase.output is None:
        # No output to compare.
        return CheckerResult(outcome=Outcome.ACCEPTED)

    if should_use_python_checker:
        # Use default wcmp checker.
        expected = testcase.output.read_text()
        output = output_path.read_text()

        return CheckerResult(outcome=_wcmp_check(expected, output))

    sandbox.params.set_stdall(
        stdin=None,
        stdout=pathlib.PosixPath('stdout.txt'),
        stderr=pathlib.PosixPath('stderr.txt'),
    )

    sandbox.create_file_from_string(
        pathlib.PosixPath('expected.txt'), testcase.output.read_text(), override=True
    )
    sandbox.create_file_from_string(
        pathlib.PosixPath('output.txt'), output_path.read_text(), override=True
    )
    sandbox.create_file_from_string(
        pathlib.PosixPath('input.txt'),
        testcase.input.read_text() if testcase.input is not None else '',
        override=True,
    )

    if not sandbox.execute_without_std(
        ['./checker', 'input.txt', 'output.txt', 'expected.txt'], wait=True
    ):
        console.print(
            '[error]Sandbox crashed while running checker.[/error]',
        )
        return CheckerResult(outcome=Outcome.INTERNAL_ERROR)

    checker_stderr = sandbox.get_file_to_string(
        pathlib.PosixPath('stderr.txt'), maxlen=None
    )
    if sandbox.get_exit_code() in [1, 2]:
        return CheckerResult(outcome=Outcome.WRONG_ANSWER, message=checker_stderr)
    if sandbox.get_exit_code() == 3:
        return CheckerResult(outcome=Outcome.JUDGE_FAILED, message=checker_stderr)
    return CheckerResult(outcome=Outcome.ACCEPTED, message=checker_stderr)


# Always assume a `checker` executable in the sandbox if should use checker.
def evaluate(
    sandbox: SandboxBase,
    testcase: TestcaseIO,
    log: Optional[TestcaseLog],
    artifacts: GradingArtifacts,
    should_use_python_checker: bool = False,
) -> Evaluation:
    if log is None:
        return Evaluation(
            testcase=testcase,
            log=TestcaseLog(),
            result=CheckerResult(outcome=Outcome.INTERNAL_ERROR),
        )
    if log.exitstatus != SandboxBase.EXIT_OK:
        return Evaluation(
            testcase=testcase,
            log=log,
            result=CheckerResult(outcome=Outcome.RUNTIME_ERROR),
        )

    if not testcase.output:
        # No output to compare.
        return Evaluation(
            testcase=testcase, log=log, result=CheckerResult(outcome=Outcome.ACCEPTED)
        )

    _process_input_artifacts(artifacts, sandbox)
    if log.stdout_absolute_path is None:
        return Evaluation(
            testcase=testcase,
            log=log,
            result=CheckerResult(outcome=Outcome.INTERNAL_ERROR, message='No output'),
        )

    checker_result = _check(
        sandbox,
        testcase,
        log.stdout_absolute_path,
        should_use_python_checker=should_use_python_checker,
    )
    return Evaluation(
        testcase=testcase,
        log=log,
        result=checker_result,
    )
