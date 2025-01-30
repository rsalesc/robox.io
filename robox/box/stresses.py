import dataclasses
import functools
import time
from shutil import rmtree
from typing import List, Optional

import typer
from pydantic import BaseModel

from robox import console
from robox.box import checkers, package, validators
from robox.box.code import compile_item, run_item
from robox.box.schema import CodeItem, GeneratorCall, Stress, Testcase
from robox.box.solutions import compile_solutions, get_outcome_style_verdict
from robox.box.stressing import finder_parser, generator_parser
from robox.grading.steps import (
    DigestHolder,
    DigestOrDest,
    DigestOrSource,
    Outcome,
)
from robox.utils import StatusProgress


class StressFinding(BaseModel):
    generator: GeneratorCall


class StressReport(BaseModel):
    findings: List[StressFinding] = []
    executed: int = 0


def _compile_finder(finder: CodeItem) -> str:
    try:
        digest = compile_item(finder)
    except Exception as e:
        console.console.print(
            f'[error]Failed compiling checker [item]{finder.path}[/item].[/error]'
        )
        raise typer.Exit(1) from e
    return digest


def run_stress(
    name: str,
    timeoutInSeconds: int,
    finder: Optional[str] = None,
    args: Optional[str] = None,
    findingsLimit: int = 1,
    verbose: bool = False,
    progress: Optional[StatusProgress] = None,
) -> StressReport:
    if finder:
        stress = Stress(
            name=f'{name}',
            generator=GeneratorCall(name=name, args=args or ''),
            finder=finder,
        )
    else:
        stress = package.get_stress(name)

    call = stress.generator
    generator = package.get_generator(call.name)

    try:
        generator_digest = compile_item(generator)
    except:
        console.console.print(
            f'[error]Failed compiling generator [item]{generator.name}[/item].[/error]'
        )
        raise

    # Finder expression parser
    parsed_finder = finder_parser.parse(stress.finder)

    solutions = finder_parser.get_all_solution_items(parsed_finder)
    finders = finder_parser.get_all_checker_items(parsed_finder)
    needs_expected_output = finder_parser.needs_expected_output(parsed_finder)

    solution_indices = {str(solution.path): i for i, solution in enumerate(solutions)}
    solutions_digest = compile_solutions(
        tracked_solutions=set(str(solution.path) for solution in solutions)
    )
    if progress:
        progress.update('Compiling finders...')
    finders_digest = {str(finder.path): _compile_finder(finder) for finder in finders}

    validator = validators.compile_main_validator()

    # Erase old stress directory
    runs_dir = package.get_problem_runs_dir()
    stress_dir = runs_dir / '.stress'
    rmtree(str(stress_dir), ignore_errors=True)
    stress_dir.mkdir(parents=True, exist_ok=True)
    empty_path = runs_dir / '.stress' / '.empty'
    empty_path.write_text('')

    startTime = time.monotonic()

    # Generator args parser
    parsed_args = generator_parser.parse(call.args or '')
    vars = package.find_problem_package_or_die().expanded_vars
    generator_for_args = generator_parser.Generator(vars)

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

        # Build generator args based on generator parse tree.
        expanded_args_str = generator_for_args.generate(parsed_args)

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
                f'[error]Failed generating test for stress test [item]{name}[/item] with args [info]{call.name} {expanded_args_str}[/info].[/error]',
            )
            if generation_stderr.value is not None:
                console.console.print('[error]Stderr:[/error]')
                console.console.print(
                    package.get_digest_as_string(generation_stderr.value) or ''
                )

            raise typer.Exit(1)

        # Run validator, if it is available.
        if validator is not None:
            ok, message, *_ = validators.validate_test(input_path, *validator)
            if not ok:
                console.console.print(
                    f'[error]Failed validating testcase for stress test [item]{name}[/item] with args [info]{call.name} {expanded_args_str}[/info].[/error]'
                )
                console.console.print(f'[error]Message:[/error] {message}')
                console.console.print(f'Testcase written at [item]{input_path}[/item]')
                raise typer.Exit(1)

        @functools.cache
        def run_solution_fn(
            solution: str,
            input_path=input_path,
        ) -> finder_parser.FinderSolutionResult:
            index = solution_indices[solution]
            sol = solutions[index]
            output_path = input_path.with_stem(f'{index}').with_suffix('.out')
            stderr_path = output_path.with_suffix('.err')

            run_log = run_item(
                sol,
                DigestOrSource.create(solutions_digest[sol.path]),
                stdin=DigestOrSource.create(input_path),
                stdout=DigestOrDest.create(output_path),
                stderr=DigestOrDest.create(stderr_path),
            )

            return finder_parser.FinderSolutionResult(
                output_path=output_path,
                stderr_path=stderr_path,
                run_log=run_log,
            )

        # Get main solution output.
        expected_output_path = empty_path
        if needs_expected_output:
            main_result = run_solution_fn(str(solutions[0].path))
            main_checker_result = checkers.check_with_no_output(main_result.run_log)
            if main_checker_result.outcome != Outcome.ACCEPTED:
                console.console.print(
                    '[error]Error while generating main solution output.[/error]'
                )
                console.console.print(f'Input written at [item]{input_path}[/item].')
                console.console.print(
                    f'Output written at [item]{main_result.output_path}[/item].'
                )
                console.console.print(
                    f'Stderr written at [item]{main_result.stderr_path}[/item].'
                )
                console.console.print()
                console.console.print(
                    "[warning]If you don't want reference outputs to be generated for the tests, you should "
                    "use the two-way modifier in your finder expression (':2')."
                )
                raise typer.Exit(1)
            expected_output_path = main_result.output_path

        @functools.cache
        def run_solution_and_checker_fn(
            solution: str,
            checker: Optional[finder_parser.FinderChecker],
            input_path=input_path,
            expected_output_path=expected_output_path,
        ) -> finder_parser.FinderResult:
            solution_result = run_solution_fn(solution)

            if checker is None:
                checker_result = checkers.check_with_no_output(solution_result.run_log)
            else:
                checker_digest = finders_digest[checker.path]
                checker_result = checkers.check(
                    checker_digest,
                    solution_result.run_log,
                    Testcase(inputPath=input_path, outputPath=expected_output_path),
                    program_output=solution_result.output_path,
                )
            return finder_parser.FinderResult(
                solution=solution,
                outcome=checker_result.outcome,
                checker=checker,
                truth_value=True,
                solution_result=solution_result,
                checker_result=checker_result,
            )

        def run_fn(
            call: finder_parser.FinderCall,
        ) -> finder_parser.FinderResult:
            finder_result = run_solution_and_checker_fn(call.solution, call.checker)
            truth_value = call.expected_outcome.match(finder_result.outcome)
            return dataclasses.replace(finder_result, truth_value=truth_value)

        runner = finder_parser.FinderTreeRunner(runner=run_fn)
        finder_outcome: finder_parser.FinderOutcome = runner.transform(parsed_finder)

        internal_error_results = [
            result
            for result in finder_outcome.results
            if result.outcome == Outcome.INTERNAL_ERROR
        ]

        if internal_error_results:
            console.console.print(
                f'[error]Checkers failed during stress test [item]{name}[/item] with args [info]{call.name} {expanded_args_str}[/info].[/error]'
            )
            for internal_error_result in internal_error_results:
                assert internal_error_result.checker is not None
                assert internal_error_result.checker_result is not None
                internal_error_checker_name = internal_error_result.checker.path
                console.console.print(
                    f'[warning]Checker [item]{internal_error_checker_name}[/item] failed with message:'
                )
                console.console.print(internal_error_result.checker_result.message)
            raise typer.Exit(1)

        if not finder_outcome.truth_value:
            continue

        if progress:
            console.console.print(
                f'[error]FINDING[/error] Generator args are "[status]{generator.name} {expanded_args_str}[/status]"'
            )
            seen_finder_results = set()
            for finder_result in finder_outcome.results:
                style = get_outcome_style_verdict(finder_result.outcome)
                finder_result_key = (finder_result.solution, finder_result.checker)
                if finder_result_key in seen_finder_results:
                    continue
                seen_finder_results.add(finder_result_key)
                finder_result_report_line = f'{finder_result.solution} = [{style}]{finder_result.outcome.name}[/{style}]'
                if finder_result.checker is not None:
                    finder_result_report_line += (
                        f' [item]ON[/item] {finder_result.checker.path}'
                    )
                console.console.print(finder_result_report_line)

        findings.append(
            StressFinding(
                generator=GeneratorCall(name=generator.name, args=expanded_args_str),
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
        console.console.print()
