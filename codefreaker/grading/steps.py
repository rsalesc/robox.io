import dataclasses
from enum import Enum
import json
import pathlib
import shlex
from typing import Dict, List, Optional

from codefreaker import utils
from codefreaker.console import console
from codefreaker.config import Artifact, Language, format_vars
from codefreaker.grading.judge.sandbox import SandboxBase
from codefreaker.grading.judge.storage import copyfileobj
from codefreaker.schema import DumpedProblem


class Outcome(Enum):
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong-answer"
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
    lang: Language,
    sandbox: SandboxBase,
    testcases: List[TestcaseIO],
    persist_root: pathlib.Path = pathlib.Path("."),
) -> Optional[Dict[int, TestcaseLog]]:
    cmd = shlex.split(lang.exec)
    logs: Dict[int, TestcaseLog] = {}

    # Ensure persist dir exists.
    persist_root.mkdir(parents=True, exist_ok=True)

    for testcase in testcases:
        if testcase.input:
            sandbox.create_file_from_string(
                pathlib.PosixPath("stdin.txt"),
                testcase.input.read_text(),
                override=True,
            )
        sandbox.params.set_stdall(
            stdin="stdin.txt" if testcase.input else None,
            stdout="stdout.txt",
            stderr="stderr.txt",
        )

        stdout_persisted_path = persist_root / f"stdout-{testcase.index}.txt"
        stderr_persisted_path = persist_root / f"stderr-{testcase.index}.txt"

        if not sandbox.execute_without_std(cmd, wait=True):
            console.print(
                "[error]Sandbox crashed while processing command:[/error]",
                utils.highlight_json_obj(cmd),
            )
            return None

        copyfileobj(sandbox.get_file("stdout.txt"), stdout_persisted_path.open("wb"))
        copyfileobj(sandbox.get_file("stderr.txt"), stderr_persisted_path.open("wb"))

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


def _check(
    sandbox: SandboxBase, expected_path: pathlib.Path, output_path: pathlib.Path
) -> Outcome:
    expected = expected_path.read_text()
    output = output_path.read_text()

    if _normalize_checked_words(expected) == _normalize_checked_words(output):
        return Outcome.ACCEPTED

    return Outcome.WRONG_ANSWER


def evaluate(
    sandbox: SandboxBase,
    testcases: List[TestcaseIO],
    testcase_logs: Dict[int, TestcaseLog],
    persist_root: pathlib.Path = pathlib.Path("."),
) -> List[TestcaseEvaluation]:
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

        evaluations.append(
            TestcaseEvaluation(
                testcase=testcase,
                log=log,
                outcome=_check(sandbox, testcase.output, log.stdout_absolute_path),
            )
        )

    return evaluations
