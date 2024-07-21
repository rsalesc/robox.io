import pathlib
import random
import shlex
import time
from typing import List, Optional, Union

import typer
from pydantic import BaseModel

from robox import console
from robox.box import checkers, package
from robox.box.code import compile_item, run_item
from robox.box.schema import GeneratorCall, Testcase
from robox.box.solutions import compile_solutions, get_outcome_style_verdict
from robox.grading.steps import (
    CheckerResult,
    DigestOrDest,
    DigestOrSource,
)
from robox.utils import StatusProgress

StressArg = Union[str, 'RandomInt', 'RandomHex', List['StressArg']]


class StressFinding(BaseModel):
    generator: GeneratorCall
    solution: pathlib.Path
    result: CheckerResult


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
) -> List[StressFinding]:
    stress = package.get_stress(name)

    call = stress.generator
    generator = package.get_generator(call.name)
    main_solution = package.get_main_solution()
    solutions = [package.get_solution(solutions) for solutions in stress.solutions]
    solutions = [main_solution] + solutions

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

    startTime = time.monotonic()
    parsed_args = parse_generator_pattern(call.args or '')
    runs_dir = package.get_problem_runs_dir()

    findings = []

    while len(findings) < findingsLimit:
        if time.monotonic() - startTime > timeoutInSeconds:
            break

        if progress:
            seconds = timeoutInSeconds - int(time.monotonic() - startTime)
            progress.update(
                f'Stress testing: found [item]{len(findings)}[/item] tests, '
                f'[item]{seconds}[/item] second(s) remaining...'
            )

        expanded_args = expand_stress_args(parsed_args)
        expanded_args_str = ' '.join(expanded_args)

        input_path = runs_dir / '.stress' / 'input'
        input_path.parent.mkdir(parents=True, exist_ok=True)

        generation_log = run_item(
            generator,
            DigestOrSource.create(generator_digest),
            stdout=DigestOrDest.create(input_path),
            extra_args=expanded_args_str or None,
        )
        if not generation_log or generation_log.exitcode != 0:
            console.console.print(
                f'Failed generating test for stress test [item]{name}[/item] with args [info]{expanded_args}[/info]',
                style='error',
            )
            raise typer.Exit(1)

        expected_output_path = runs_dir / '.stress' / 'output'
        for i, solution in enumerate(solutions):
            if solution is None:
                continue
            output_path = input_path.with_stem(f'{i}').with_suffix('.out')
            if i == 0:
                # This is the main solution.
                expected_output_path = output_path

            run_log = run_item(
                solution,
                DigestOrSource.create(solutions_digest[solution.path]),
                stdin=DigestOrSource.create(input_path),
                stdout=DigestOrDest.create(output_path),
            )

            checker_result = checkers.check(
                checker_digest,
                run_log,
                Testcase(inputPath=input_path, outputPath=expected_output_path),
                program_output=output_path,
            )

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
        time.sleep(0.001)

    return findings


def print_stress_report(findings: List[StressFinding]):
    console.console.rule('Stress test report', style='status')
    if not findings:
        console.console.print('[info]No stress test findings.[/info]')
        return

    for i, finding in enumerate(findings):
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
