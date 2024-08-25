import pathlib
from typing import Optional

from robox import console
from robox.box import package
from robox.box.code import compile_item, run_item
from robox.box.schema import Testcase
from robox.grading.judge.sandbox import SandboxBase
from robox.grading.steps import (
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

    try:
        digest = compile_item(checker)
    except:
        console.console.print('[error]Failed compiling checker.[/error]')
        raise
    return digest


def _check_pre_output(run_log: Optional[RunLog]) -> CheckerResult:
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
    return CheckerResult(outcome=Outcome.ACCEPTED)


def _convert_tle(result: CheckerResult, run_log: Optional[RunLog]) -> CheckerResult:
    pkg = package.find_problem_package_or_die()
    if (
        run_log is not None
        and run_log.time is not None
        and run_log.time * 1000 > pkg.timeLimit
    ):
        # Soft TLE.
        result.no_tle_outcome = result.outcome
        result.outcome = Outcome.TIME_LIMIT_EXCEEDED
    return result


def check_with_no_output(run_log: Optional[RunLog]) -> CheckerResult:
    result = _check_pre_output(run_log)
    return _convert_tle(result, run_log)


def check(
    checker_digest: str,
    run_log: Optional[RunLog],
    testcase: Testcase,
    program_output: pathlib.Path,
) -> CheckerResult:
    result = _check_pre_output(run_log)
    if result.outcome != Outcome.ACCEPTED:
        return _convert_tle(result, run_log)

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

    message = package.get_digest_as_string(error.value or '') or ''

    if checker_run_log is None or checker_run_log.exitcode not in [0, 1, 2, 3]:
        return CheckerResult(outcome=Outcome.INTERNAL_ERROR)

    result = CheckerResult(outcome=Outcome.ACCEPTED, message=message)

    if checker_run_log.exitcode in [1, 2]:
        result = CheckerResult(outcome=Outcome.WRONG_ANSWER, message=message)
    if checker_run_log.exitcode == 3:
        result = CheckerResult(outcome=Outcome.JUDGE_FAILED, message=message)

    return _convert_tle(result, run_log)
