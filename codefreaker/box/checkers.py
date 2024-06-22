import pathlib
from typing import Optional

from codefreaker.box import package
from codefreaker.box.code import compile_item, run_item
from codefreaker.box.schema import Testcase
from codefreaker.grading.judge.sandbox import SandboxBase
from codefreaker.grading.steps import (
    CheckerResult,
    DigestHolder,
    DigestOrDest,
    DigestOrSource,
    GradingFileInput,
    Outcome,
    RunLog,
)


def compile_checker() -> str:
    checker = package.get_checker()

    return compile_item(checker)


def check(
    checker_digest: str,
    run_log: Optional[RunLog],
    testcase: Testcase,
    program_output: pathlib.Path,
) -> CheckerResult:
    pkg = package.find_problem_package_or_die()

    if run_log is None:
        return CheckerResult(outcome=Outcome.INTERNAL_ERROR)

    if run_log.time is not None and run_log.time * 1000 > pkg.timeLimit * 2:
        return CheckerResult(outcome=Outcome.TIME_LIMIT_EXCEEDED)

    if run_log.exitstatus in [SandboxBase.EXIT_SIGNAL, SandboxBase.EXIT_NONZERO_RETURN]:
        return CheckerResult(outcome=Outcome.RUNTIME_ERROR)
    if run_log.exitstatus in [SandboxBase.EXIT_TIMEOUT, SandboxBase.EXIT_TIMEOUT_WALL]:
        return CheckerResult(outcome=Outcome.TIME_LIMIT_EXCEEDED)
    if run_log.exitstatus == SandboxBase.EXIT_MEMORY_LIMIT_EXCEEDED:
        return CheckerResult(outcome=Outcome.MEMORY_LIMIT_EXCEEDED)
    if run_log.exitstatus == SandboxBase.EXIT_SANDBOX_ERROR:
        return CheckerResult(outcome=Outcome.INTERNAL_ERROR)

    error = DigestHolder()
    inputs = [
        GradingFileInput(
            src=testcase.inputPath,
            dest=pathlib.PosixPath('input.txt'),
        ),
        GradingFileInput(
            src=testcase.outputPath,
            dest=pathlib.PosixPath('expected.txt'),
        ),
        GradingFileInput(
            src=program_output,
            dest=pathlib.PosixPath('output.txt'),
        ),
    ]
    checker_run_log = run_item(
        package.get_checker(),
        DigestOrSource.create(checker_digest),
        stderr=DigestOrDest.create(error),
        inputs=inputs,
        extra_args='input.txt output.txt expected.txt',
    )

    if checker_run_log is None or checker_run_log.exitcode not in [0, 1, 2, 3]:
        return CheckerResult(outcome=Outcome.INTERNAL_ERROR)

    message = package.get_digest_as_string(error.value or '') or ''

    result = CheckerResult(outcome=Outcome.ACCEPTED, message=message)

    if checker_run_log.exitcode in [1, 2]:
        result = CheckerResult(outcome=Outcome.WRONG_ANSWER, message=message)
    if checker_run_log.exitcode == 3:
        result = CheckerResult(outcome=Outcome.JUDGE_FAILED, message=message)

    if run_log.time is not None and run_log.time * 1000 > pkg.timeLimit:
        # Soft TLE.
        result.no_tle_outcome = result.outcome
        result.outcome = Outcome.TIME_LIMIT_EXCEEDED
    return result
