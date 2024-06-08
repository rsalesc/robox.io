import dataclasses
from enum import Enum
import json
import pathlib
import shlex
from typing import Dict, List, Optional

from rich.progress import Progress, SpinnerColumn, MofNCompleteColumn

from codefreaker import utils
from codefreaker.console import console
from codefreaker.config import (
    Artifact,
    Language,
    format_vars,
    get_app_path,
    get_builtin_checker,
)
from codefreaker.grading.judge.sandbox import SandboxBase, MERGE_STDERR
from codefreaker.grading.judge.storage import copyfileobj
from codefreaker.schema import DumpedProblem, Problem

MAX_STDOUT_LEN = 1024 * 1024 * 128  # 128 MB


class Outcome(Enum):
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong-answer"
    JUDGE_FAILED = "judge-failed"
    RUNTIME_ERROR = "runtime-error"
    TIME_LIMIT_EXCEEDED = "time-limit-exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory-limit-exceeded"
    OUTPUT_LIMIT_EXCEEDED = "output-limit-exceeded"
    INTERNAL_ERROR = "internal-error"


@dataclasses.dataclass
class TestcaseIO:
    index: int
    input: Optional[pathlib.Path] = None
    output: Optional[pathlib.Path] = None


@dataclasses.dataclass
class PreprocessLog:
    cmd: List[str]
    exitcode: int
    log: str


@dataclasses.dataclass
class TestcaseLog:
    exitcode: int
    exitstatus: str
    time: float

    stdout_absolute_path: pathlib.Path
    stderr_absolute_path: pathlib.Path


@dataclasses.dataclass
class TestcaseEvaluation:
    testcase: TestcaseIO
    log: TestcaseLog
    outcome: Outcome
    message: str = ""


@dataclasses.dataclass
class CheckerResult:
    outcome: Outcome
    message: str = ""


def preprocess(
    problem: DumpedProblem,
    lang: Language,
    sandbox: SandboxBase,
    root: pathlib.Path = pathlib.Path("."),
) -> bool:
    file = root / lang.get_file(problem.code)
    submit_file = root / lang.get_submit_file(problem.code)

    if not file.is_file():
        console.print(f"[error]File {file} does not exist.[/error]")
        return False

    sandbox.create_file_from_string(file.relative_to(root), file.read_text())

    commands = lang.preprocess or []
    if not commands:
        # Code does not need preprocessing of any kind.
        return True

    logs: List[PreprocessLog] = []

    for i, command in enumerate(commands):
        formatted_command = format_vars(
            command,
            **problem.get_vars(),
            file=str(file.relative_to(root)),
            submit_file=str(submit_file.relative_to(root)),
        )
        cmd = shlex.split(formatted_command)
        stderr_file = f"preprocess-{i}.stderr"
        sandbox.params.set_stdall(stderr=stderr_file)

        if not sandbox.execute_without_std(cmd, wait=True):
            console.print(
                "[error]Sandbox crashed while processing command:[/error]",
                utils.highlight_json_obj(cmd),
            )
            return False

        log = PreprocessLog(
            cmd=cmd,
            exitcode=sandbox.get_exit_code(),
            log=(
                sandbox.get_file_to_string(stderr_file, maxlen=None)
                if sandbox.file_exists(stderr_file)
                else ""
            ),
        )
        logs.append(log)

        if log.exitcode != 0:
            break

    if logs and logs[-1].exitcode != 0:
        console.print(
            "Preprocessing [error]failed[/error] with command",
            utils.highlight_json_obj(logs[-1].cmd),
        )
        console.print(f"Exit code: [error]{logs[-1].exitcode}[/error]")
        console.print()
        print(logs[-1].log)
        return False

    if lang.has_submit_file():
        if not sandbox.file_exists(submit_file.relative_to(root)):
            console.print(
                f"[error]Submit file [item]{submit_file}[/item] does not exist after preprocessing.[/error]"
            )
            return False
        submit_file.write_text(
            sandbox.get_file_to_string(submit_file.relative_to(root), maxlen=None)
        )

    for artifact_name, artifact_cfg in lang.artifacts.items():
        if artifact_cfg is None:
            artifact_cfg = Artifact()
        artifact_path = format_vars(
            artifact_name,
            **problem.get_vars(),
            file=str(file.relative_to(root)),
            submit_file=str(submit_file.relative_to(root)),
        )
        if not sandbox.file_exists(artifact_path) and not artifact_cfg.optional:
            console.print(
                f"[error]Artifact {artifact_path} does not exist after preprocessing.[/error]"
            )
            return False
        artifact_dest_path = root / (artifact_cfg.filename or artifact_path)
        copyfileobj(
            sandbox.get_file(artifact_path),
            artifact_dest_path.open("wb"),
        )
        if artifact_cfg.executable:
            artifact_dest_path.chmod(0o755)

    return True


def run(
    problem: Problem,
    lang: Language,
    sandbox: SandboxBase,
    testcases: List[TestcaseIO],
    persist_root: pathlib.Path = pathlib.Path("."),
) -> Optional[Dict[int, TestcaseLog]]:
    cmd = shlex.split(lang.exec)
    logs: Dict[int, TestcaseLog] = {}

    # Ensure persist dir exists.
    persist_root.mkdir(parents=True, exist_ok=True)

    time_limit = problem.timeLimit or 1000
    sandbox.params.timeout = time_limit * 2
    sandbox.params.wallclock_timeout = time_limit * 5
    sandbox.params.address_space = 1024  # 1 GB

    progress = Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        MofNCompleteColumn(),
        transient=True,
    )
    with progress:
        for testcase in progress.track(testcases, description="Running testcases..."):
            if testcase.input:
                sandbox.create_file_from_string(
                    pathlib.PosixPath("stdin.txt"),
                    testcase.input.read_text(),
                    override=True,
                )
            sandbox.params.set_stdall(
                stdin="stdin.txt" if testcase.input else None,
                stdout="stdout.txt",
                stderr=MERGE_STDERR,
            )

            stdout_persisted_path = persist_root / f"stdout-{testcase.index}.txt"
            stderr_persisted_path = persist_root / f"stderr-{testcase.index}.txt"

            if not sandbox.execute_without_std(cmd, wait=True):
                console.print(
                    "[error]Sandbox crashed while processing command:[/error]",
                    utils.highlight_json_obj(cmd),
                )
                return None

            copyfileobj(
                sandbox.get_file("stdout.txt"),
                stdout_persisted_path.open("wb"),
                maxlen=MAX_STDOUT_LEN,
            )

            log = TestcaseLog(
                exitcode=sandbox.get_exit_code(),
                exitstatus=sandbox.get_exit_status(),
                time=sandbox.get_execution_time(),
                stdout_absolute_path=stdout_persisted_path.absolute(),
                stderr_absolute_path=stderr_persisted_path.absolute(),
            )
            logs[testcase.index] = log

    return logs


def _normalize_checked_words(s: str) -> List[str]:
    return tuple(s.split())


def _wcmp_check(expected: str, output: str) -> Outcome:
    if _normalize_checked_words(expected) == _normalize_checked_words(output):
        return Outcome.ACCEPTED

    return Outcome.WRONG_ANSWER


def _compile_checker(checker: str, sandbox: SandboxBase) -> bool:
    sandbox.params.set_stdall(
        stdin=None,
        stdout="stdout.txt",
        stderr="stderr.txt",
    )

    checker_path = pathlib.Path(checker)
    if not checker_path.is_file():
        checker_path = get_builtin_checker(checker)
    if not checker_path.is_file():
        console.print(f"[error]Checker {checker_path} does not exist.[/error]")
        return False

    testlib = get_builtin_checker("testlib.h")
    if not testlib.is_file():
        console.print(f"[error]Testlib was not found in {testlib}.[/error]")
        return False

    sandbox.create_file_from_string(
        "checker.cpp", checker_path.read_text(), override=True
    )
    sandbox.create_file_from_string("testlib.h", testlib.read_text(), override=True)

    cmd = ["g++", "-std=c++17", "-o", "checker", "checker.cpp"]
    if not sandbox.execute_without_std(cmd, wait=True):
        console.print(
            "[error]Sandbox crashed while processing command:[/error]",
            utils.highlight_json_obj(cmd),
        )
        return False
    if sandbox.get_exit_code() != 0:
        console.print(
            "[error]Checker compilation failed with exit code:[/error]",
            sandbox.get_exit_code(),
        )
        print(sandbox.get_file_to_string("stderr.txt", maxlen=None))
        return False
    return True


def _check(
    problem: DumpedProblem,
    sandbox: SandboxBase,
    testcase: TestcaseIO,
    output_path: pathlib.Path,
) -> CheckerResult:
    if not problem.checker:
        # Use default wcmp checker.
        expected = testcase.output.read_text()
        output = output_path.read_text()

        return CheckerResult(outcome=_wcmp_check(expected, output))

    sandbox.params.set_stdall(
        stdin=None,
        stdout="stdout.txt",
        stderr="stderr.txt",
    )

    sandbox.create_file_from_string(
        "expected.txt", testcase.output.read_text(), override=True
    )
    sandbox.create_file_from_string(
        "output.txt", output_path.read_text(), override=True
    )
    sandbox.create_file_from_string(
        "input.txt", testcase.input.read_text(), override=True
    )

    if not sandbox.execute_without_std(
        ["./checker", "input.txt", "output.txt", "expected.txt"], wait=True
    ):
        console.print(
            "[error]Sandbox crashed while running checker.[/error]",
        )
        return CheckerResult(outcome=Outcome.INTERNAL_ERROR)

    stderr = sandbox.get_file_to_string("stderr.txt", maxlen=None)
    if sandbox.get_exit_code() in [1, 2]:
        return CheckerResult(outcome=Outcome.WRONG_ANSWER, message=stderr)
    if sandbox.get_exit_code() == 3:
        return CheckerResult(outcome=Outcome.JUDGE_FAILED, message=stderr)
    return CheckerResult(outcome=Outcome.ACCEPTED, message=stderr)


def evaluate(
    problem: DumpedProblem,
    sandbox: SandboxBase,
    testcases: List[TestcaseIO],
    testcase_logs: Dict[int, TestcaseLog],
    persist_root: pathlib.Path = pathlib.Path("."),
) -> List[TestcaseEvaluation]:
    if problem.checker:
        if not _compile_checker(problem.checker, sandbox):
            return []

    evaluations = []
    for testcase in testcases:
        if testcase.index not in testcase_logs:
            continue

        log = testcase_logs[testcase.index]
        if log.exitstatus != SandboxBase.EXIT_OK:
            evaluations.append(
                TestcaseEvaluation(
                    testcase=testcase,
                    log=log,
                    outcome=Outcome.RUNTIME_ERROR,
                )
            )
            continue

        if not testcase.output:
            # No output to compare.
            evaluations.append(
                TestcaseEvaluation(testcase=testcase, log=log, outcome=Outcome.ACCEPTED)
            )
            continue

        checker_result = _check(problem, sandbox, testcase, log.stdout_absolute_path)
        evaluations.append(
            TestcaseEvaluation(
                testcase=testcase,
                log=log,
                outcome=checker_result.outcome,
                message=checker_result.message,
            )
        )

    return evaluations
