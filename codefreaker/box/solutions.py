import collections
from typing import Dict, List, Optional

import rich

from codefreaker.box import checkers, package
from codefreaker.box.code import compile_item, run_item
from codefreaker.box.environment import EnvironmentSandbox, ExecutionConfig
from codefreaker.box.schema import Solution
from codefreaker.box.testcases import find_built_testcases
from codefreaker.grading.steps import (
    DigestOrDest,
    DigestOrSource,
    Evaluation,
    Outcome,
    TestcaseIO,
    TestcaseLog,
)
from codefreaker.utils import StatusProgress


def compile_solutions(progress: Optional[StatusProgress] = None):
    pkg = package.find_problem_package_or_die()

    compiled_solutions = {}

    for solution in pkg.solutions:
        if progress:
            progress.update(f'Compiling solution [item]{solution.path}[/item]...')
        compiled_solutions[solution.path] = compile_item(solution)

    return compiled_solutions


def run_solution(
    solution: Solution,
    compiled_digest: str,
    checker_digest: str,
    index: int,
    progress: Optional[StatusProgress] = None,
) -> Dict[str, List[Evaluation]]:
    pkg = package.find_problem_package_or_die()

    sandbox = EnvironmentSandbox()
    sandbox.timeLimit = pkg.timeLimit * 2
    sandbox.wallTimeLimit = pkg.timeLimit * 2
    sandbox.memoryLimit = pkg.memoryLimit
    extra_config = ExecutionConfig(sandbox=sandbox)

    res = collections.defaultdict(list)

    for group in pkg.testcases:
        testcases = find_built_testcases(group)
        for i, testcase in enumerate(testcases):
            runs_dir = package.get_problem_runs_dir()
            assert testcase.outputPath is not None
            output_path = runs_dir / f'{index}' / group.name / testcase.outputPath.name
            error_path = (
                runs_dir
                / f'{index}'
                / group.name
                / testcase.outputPath.with_suffix('.err').name
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if progress:
                progress.update(
                    f'Running solution [item]{solution.path}[/item] on test [item]{group.name}[/item] / [item]{i}[/item]...'
                )
            run_log = run_item(
                solution,
                DigestOrSource.create(compiled_digest),
                stdin=DigestOrSource.create(testcase.inputPath),
                stdout=DigestOrDest.create(output_path),
                stderr=DigestOrDest.create(error_path),
                extra_config=extra_config,
            )

            checker_result = checkers.check(
                checker_digest,
                run_log,
                testcase,
                program_output=output_path,
            )
            res[group.name].append(
                Evaluation(
                    result=checker_result,
                    testcase=TestcaseIO(
                        index=i, input=testcase.inputPath, output=testcase.outputPath
                    ),
                    log=TestcaseLog(
                        **(run_log.model_dump() if run_log is not None else {}),
                        stdout_absolute_path=output_path.absolute(),
                        stderr_absolute_path=error_path.absolute(),
                    ),
                )
            )

    return dict(res)


def run_solutions(progress: StatusProgress) -> List[Dict[str, List[Evaluation]]]:
    pkg = package.find_problem_package_or_die()

    checker_digest = checkers.compile_checker()
    compiled_solutions = compile_solutions(progress=progress)
    res = []

    for i, solution in enumerate(pkg.solutions):
        results_per_group = run_solution(
            solution,
            compiled_solutions[solution.path],
            checker_digest,
            i,
            progress=progress,
        )
        res.append(results_per_group)

    return res


def _get_testcase_markup_verdict(eval: Evaluation) -> str:
    res = '[green]✓[/green]'
    if eval.result.outcome != Outcome.ACCEPTED:
        res = '[red]✗[/red]'
    if eval.result.outcome == Outcome.TIME_LIMIT_EXCEEDED:
        res = '[yellow]⧖[/yellow]'
    if eval.result.outcome == Outcome.RUNTIME_ERROR:
        res = '[lnumber]✗[/lnumber]'
    if eval.log.stdout_absolute_path:
        output_path = eval.log.stdout_absolute_path.resolve()
        output_link = f'file://{output_path}'
        res = f'[link={output_link}]{res}[/link]'
    return res


def _print_solution_outcome(
    solution: Solution, evals: List[Evaluation], console: rich.console.Console
):
    first_non_match = None
    max_time = 0.0
    for eval in evals:
        max_time = max(max_time, eval.log.time or 0.0)
        if not solution.outcome.match(eval.result.outcome):
            first_non_match = eval
            break

    console.print(f'Expected: {solution.outcome}', end='')
    if first_non_match is not None:
        all_non_matching_outcomes = set(
            eval.result.outcome.name
            for eval in evals
            if not solution.outcome.match(eval.result.outcome)
        )
        console.print(f', actually got: {" ".join(all_non_matching_outcomes)}', end='')
    console.print()
    if max_time > 1e-3:
        console.print(f'Time: {max_time or 0.0:.2f}s')


def print_run_report(
    evals_per_solution: List[Dict[str, List[Evaluation]]],
    console: rich.console.Console,
):
    pkg = package.find_problem_package_or_die()

    for s, (solution, evals_per_group) in enumerate(
        zip(pkg.solutions, evals_per_solution)
    ):
        solution_testdir = package.get_problem_runs_dir() / f'{s}'
        console.print(f'[item]{solution.path}[/item]', end=' ')
        console.print(f'({solution_testdir})')

        all_evals = []
        for group, evals in evals_per_group.items():
            console.print(f'[bold][status]{group}[/status][/bold]', end=' ')
            for i, eval in enumerate(evals):
                console.print(f'{i}/', end='')
                console.print(_get_testcase_markup_verdict(eval), end=' ')
            console.print()
            all_evals.extend(evals)

        _print_solution_outcome(solution, all_evals, console)
