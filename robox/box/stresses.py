import pathlib
import random
import shlex
import time
from shutil import rmtree
from typing import List, Optional, Union

import typer
from pydantic import BaseModel

from robox import console
from robox.box import checkers, package, validators
from robox.box.code import compile_item, run_item
from robox.box.schema import GeneratorCall, Testcase
from robox.box.solutions import compile_solutions, get_outcome_style_verdict
from robox.grading.steps import (
    CheckerResult,
    DigestHolder,
    DigestOrDest,
    DigestOrSource,
    Outcome,
)
from robox.utils import StatusProgress

StressArg = Union[str, 'RandomInt', 'RandomHex', List['StressArg']]


class StressFinding(BaseModel):
    generator: GeneratorCall
    solution: pathlib.Path
    result: CheckerResult


class StressReport(BaseModel):
    findings: List[StressFinding] = []
    executed: int = 0


class RandomInt:
    def __init__(self, min: int, max: int):
        self.min = min
        self.max = max

    def get(self) -> int:
        return random.randint(self.min, self.max)


class RandomHex:
    len: int

    def __init__(self, len: int):
        self.len = len

    def get(self) -> str:
        return ''.join(random.choice('0123456789abcdef') for _ in range(self.len))


def _parse_random_choice(pattern: str) -> List[StressArg]:
    # TODO: Add escaping for |
    return [_parse_single_pattern(choice) for choice in pattern.split('|')]


def _parse_var(name: str) -> str:
    pkg = package.find_problem_package_or_die()

    if name not in pkg.vars:
        console.console.print(f'[error]Variable [item]{name}[/item] not found.[/error]')
        raise typer.Exit(1)
    return f'{pkg.expanded_vars[name]}'


def _parse_int(pattern: str) -> int:
    if pattern.startswith('<') and pattern.endswith('>'):
        return int(_parse_var(pattern[1:-1]))
    return int(pattern)


def _parse_random_int(pattern: str) -> RandomInt:
    min, max = pattern.split('..')
    return RandomInt(_parse_int(min), _parse_int(max))


def _parse_single_pattern(pattern: str) -> StressArg:
    if pattern.startswith('\\'):
        # Escape
        return pattern[1:]
    if pattern.startswith('<') and pattern.endswith('>'):
        return _parse_var(pattern[1:-1])
    if pattern.startswith('[') and pattern.endswith(']'):
        # Random range
        return _parse_random_int(pattern[1:-1])
    if pattern.startswith('(') and pattern.endswith(')'):
        return _parse_random_choice(pattern[1:-1])
    if pattern == '@':
        return RandomHex(len=8)
    return pattern


def parse_generator_pattern(args: str) -> List[StressArg]:
    return [_parse_single_pattern(arg) for arg in shlex.split(args)]


def _expand_single_arg(arg: StressArg) -> str:
    if isinstance(arg, RandomInt):
        return str(arg.get())
    if isinstance(arg, RandomHex):
        return arg.get()
    if isinstance(arg, list):
        return _expand_single_arg(random.choice(arg))
    return str(arg)


def expand_stress_args(pattern: List[StressArg]) -> List[str]:
    return [_expand_single_arg(arg) for arg in pattern]


def run_stress(
    name: str,
    timeoutInSeconds: int,
    findingsLimit: int = 1,
    progress: Optional[StatusProgress] = None,
) -> StressReport:
    # TODO: show proper errors at each compilation error.
    stress = package.get_stress(name)

    call = stress.generator
    generator = package.get_generator(call.name)
    main_solution = package.get_main_solution()
    solutions = [package.get_solution(solutions) for solutions in stress.solutions]
    solutions = [main_solution] + solutions
    is_main_stress = not stress.solutions

    try:
        generator_digest = compile_item(generator)
    except:
        console.console.print(
            f'[error]Failed compiling generator [item]{generator.name}[/item].[/error]'
        )
        raise
    checker_digest = checkers.compile_checker()
    solutions_digest = compile_solutions(
        tracked_solutions=set(
            str(solution.path) for solution in solutions if solution is not None
        )
    )

    validator = validators.compile_main_validator()

    # Erase old stress directory
    runs_dir = package.get_problem_runs_dir()
    stress_dir = runs_dir / '.stress'
    rmtree(str(stress_dir), ignore_errors=True)
    stress_dir.mkdir(parents=True, exist_ok=True)

    startTime = time.monotonic()
    parsed_args = parse_generator_pattern(call.args or '')

    executed = 0
    findings = []

    while len(findings) < findingsLimit:
        if time.monotonic() - startTime > timeoutInSeconds:
            break

        if progress:
            seconds = timeoutInSeconds - int(time.monotonic() - startTime)
            progress.update(
                f'Stress testing: found [item]{len(findings)}[/item] tests, '
                f'executed [item]{executed}[/item], '
                f'[item]{seconds}[/item] second(s) remaining...'
            )

        expanded_args = expand_stress_args(parsed_args)
        expanded_args_str = ' '.join(expanded_args)

        input_path = runs_dir / '.stress' / 'input'
        input_path.parent.mkdir(parents=True, exist_ok=True)
        generation_stderr = DigestHolder()

        generation_log = run_item(
            generator,
            DigestOrSource.create(generator_digest),
            stdout=DigestOrDest.create(input_path),
            stderr=DigestOrDest.create(generation_stderr),
            extra_args=expanded_args_str or None,
        )
        if not generation_log or generation_log.exitcode != 0:
            console.console.print(
                f'[error]Failed generating test for stress test [item]{name}[/item] with args [info]{call.name} {expanded_args}[/info].[/error]',
            )
            if generation_stderr.value is not None:
                console.console.print('[error]Stderr:[/error]')
                console.console.print(
                    package.get_digest_as_string(generation_stderr.value) or ''
                )

            raise typer.Exit(1)

        if validator is not None:
            ok, message, *_ = validators.validate_test(input_path, *validator)
            if not ok:
                console.console.print(
                    f'[error]Failed validating testcase for stress test [item]{name}[/item] with args [info]{call.name} {expanded_args}[/info].[/error]'
                )
                console.console.print(f'[error]Message:[/error] {message}')
                console.console.print(f'Testcase written at [item]{input_path}[/item]')
                raise typer.Exit(1)

        expected_output_path = runs_dir / '.stress' / 'output'
        for i, solution in enumerate(solutions):
            if solution is None:
                continue
            output_stem = f'{i}' if i > 0 else 'main'
            output_path = input_path.with_stem(output_stem).with_suffix('.out')
            if i == 0:
                # This is the main solution.
                expected_output_path = output_path

            stderr_path = output_path.with_suffix('.err')
            run_log = run_item(
                solution,
                DigestOrSource.create(solutions_digest[solution.path]),
                stdin=DigestOrSource.create(input_path),
                stdout=DigestOrDest.create(output_path),
                # Log stderr for main solution.
                stderr=DigestOrDest.create(stderr_path) if i == 0 else None,
            )

            checker_result = checkers.check(
                checker_digest,
                run_log,
                Testcase(inputPath=input_path, outputPath=expected_output_path),
                program_output=output_path,
            )

            if checker_result.outcome == Outcome.INTERNAL_ERROR:
                console.console.print(
                    f'[error]Checker failed during stress test [item]{name}[/item] with args [info]{call.name} {expanded_args}[/info].[/error]'
                )
                console.console.print('[error]Message:[/error]')
                console.console.print(checker_result.message)
                raise typer.Exit(1)

            if (
                i == 0
                and not is_main_stress
                and checker_result.outcome != Outcome.ACCEPTED
            ):
                console.console.print(
                    '[error]Error while generating main solution output.[/error]'
                )
                console.console.print(f'Input written at [item]{input_path}[/item].')
                console.console.print(f'Output written at [item]{output_path}[/item].')
                console.console.print(f'Stderr written at [item]{stderr_path}[/item].')
                console.console.print()
                console.console.print(
                    '[warning]If you intended to stress test the main solution, '
                    're-run this stress test with the [item]stress.solutions[/item] unset.[/warning]'
                )
                raise typer.Exit(1)

            if not stress.outcome.match(checker_result.outcome):
                continue

            if progress:
                console.console.print(
                    f'[error]FINDING[/error] Generator args are "[status]{generator.name} {expanded_args_str}[/status]"'
                )

            findings.append(
                StressFinding(
                    generator=GeneratorCall(
                        name=generator.name, args=expanded_args_str
                    ),
                    solution=solution.path,
                    result=checker_result,
                )
            )

        # Be cooperative.
        executed += 1
        time.sleep(0.001)

    return StressReport(findings=findings, executed=executed)


def print_stress_report(report: StressReport):
    console.console.rule('Stress test report', style='status')
    console.console.print(f'Executed [item]{report.executed}[/item] tests.')
    if not report.findings:
        console.console.print('No stress test findings.')
        return
    console.console.print(f'Found [item]{len(report.findings)}[/item] testcases.')
    console.console.print()

    for i, finding in enumerate(report.findings):
        console.console.print(f'[error]Finding {i + 1}[/error]')
        console.console.print(
            f'Generator: [status]{finding.generator.name} {finding.generator.args}[/status]'
        )
        console.console.print(f'Solution: [item]{finding.solution}[/item]')
        style = get_outcome_style_verdict(finding.result.outcome)
        console.console.print(
            f'Outcome: [{style}]{finding.result.outcome.name}[/{style}]'
        )
        console.console.print(f'Message: [status]{finding.result.message}[/status]')
        console.console.print()
