import collections
import pathlib
from typing import Any, Dict, List, Optional, Set

import rich
import rich.table

from robox import console
from robox.box import checkers, environment, package
from robox.box.code import compile_item, run_item
from robox.box.environment import EnvironmentSandbox, ExecutionConfig, VerificationLevel
from robox.box.schema import Solution
from robox.box.testcases import find_built_testcases
from robox.grading.steps import (
    DigestOrDest,
    DigestOrSource,
    Evaluation,
    Outcome,
    TestcaseIO,
    TestcaseLog,
)
from robox.utils import StatusProgress, model_to_yaml


def is_fast(solution: Solution) -> bool:
    # If solution has TLE tag, it is considered slow.
    return not solution.outcome.match(Outcome.TIME_LIMIT_EXCEEDED)


def compile_solutions(
    progress: Optional[StatusProgress] = None,
    tracked_solutions: Optional[Set[str]] = None,
) -> Dict[pathlib.Path, str]:
    pkg = package.find_problem_package_or_die()

    compiled_solutions = {}

    for solution in pkg.solutions:
        if (
            tracked_solutions is not None
            and str(solution.path) not in tracked_solutions
        ):
            continue
        if progress:
            progress.update(f'Compiling solution [item]{solution.path}[/item]...')
        try:
            compiled_solutions[solution.path] = compile_item(solution)
        except:
            console.console.print(
                f'[error]Failed compiling solution [item]{solution.path}[/item].[/error]'
            )
            raise

    return compiled_solutions


def run_solution(
    solution: Solution,
    compiled_digest: str,
    checker_digest: Optional[str],
    index: int,
    progress: Optional[StatusProgress] = None,
    verification: VerificationLevel = VerificationLevel.NONE,
) -> Dict[str, List[Evaluation]]:
    pkg = package.find_problem_package_or_die()

    actual_sandbox = package.get_singleton_sandbox()

    sandbox = EnvironmentSandbox()
    sandbox.timeLimit = pkg.timeLimit
    if verification.value >= VerificationLevel.FULL.value:
        # Use double TL.
        sandbox.timeLimit = sandbox.timeLimit * 2
    sandbox.wallTimeLimit = (
        pkg.timeLimit * 2 if actual_sandbox.use_soft_timeout() else sandbox.timeLimit
    )
    sandbox.memoryLimit = pkg.memoryLimit
    extra_config = ExecutionConfig(sandbox=sandbox)

    res = collections.defaultdict(list)

    for group in pkg.testcases:
        testcases = find_built_testcases(group)
        for i, testcase in enumerate(testcases):
            runs_dir = package.get_problem_runs_dir()
            assert testcase.outputPath is not None
            output_path = runs_dir / f'{index}' / group.name / testcase.outputPath.name
            error_path = output_path.with_suffix('.err')
            log_path = output_path.with_suffix('.log')
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

            if checker_digest is not None:
                checker_result = checkers.check(
                    checker_digest,
                    run_log,
                    testcase,
                    program_output=output_path,
                )
            else:
                checker_result = checkers.check_with_no_output(run_log)

            eval = Evaluation(
                result=checker_result,
                testcase=TestcaseIO(
                    index=i, input=testcase.inputPath, output=testcase.outputPath
                ),
                log=TestcaseLog(
                    **(run_log.model_dump() if run_log is not None else {}),
                    stdout_absolute_path=output_path.absolute(),
                    stderr_absolute_path=error_path.absolute(),
                    log_absolute_path=log_path.absolute(),
                ),
            )

            log_path.write_text(model_to_yaml(eval))

            res[group.name].append(eval)

    return dict(res)


def run_solutions(
    progress: Optional[StatusProgress] = None,
    tracked_solutions: Optional[Set[str]] = None,
    verification: VerificationLevel = VerificationLevel.NONE,
    check: bool = True,
) -> List[Dict[str, List[Evaluation]]]:
    pkg = package.find_problem_package_or_die()

    checker_digest = checkers.compile_checker() if check else None
    compiled_solutions = compile_solutions(
        progress=progress, tracked_solutions=tracked_solutions
    )
    res = []

    for i, solution in enumerate(pkg.solutions):
        if (
            tracked_solutions is not None
            and str(solution.path) not in tracked_solutions
        ):
            res.append({})
            continue
        results_per_group = run_solution(
            solution,
            compiled_solutions[solution.path],
            checker_digest,
            i,
            progress=progress,
            verification=verification,
        )
        res.append(results_per_group)

    return res


def get_outcome_style_verdict(outcome: Outcome) -> str:
    if outcome == Outcome.ACCEPTED:
        return 'green'
    if outcome == Outcome.WRONG_ANSWER:
        return 'red'
    if outcome == Outcome.TIME_LIMIT_EXCEEDED:
        return 'yellow'
    if outcome == Outcome.RUNTIME_ERROR:
        return 'lnumber'
    if outcome == Outcome.MEMORY_LIMIT_EXCEEDED:
        return 'cyan'
    return 'magenta'


def _get_testcase_markup_verdict(eval: Evaluation) -> str:
    res = '✓'
    if eval.result.outcome != Outcome.ACCEPTED:
        res = '✗'
    if eval.result.outcome == Outcome.TIME_LIMIT_EXCEEDED:
        res = '⧖'
    if eval.result.outcome == Outcome.RUNTIME_ERROR:
        res = '✗'
    style = get_outcome_style_verdict(eval.result.outcome)
    res = f'[{style}]{res}[/{style}]'
    if eval.log.stdout_absolute_path:
        output_path = eval.log.stdout_absolute_path.resolve()
        output_link = f'file://{output_path}'
        res = f'[link={output_link}]{res}[/link]'
    return res


def _get_evals_time_in_ms(evals: List[Evaluation]) -> int:
    return max(int((eval.log.time or 0.0) * 1000) for eval in evals)


def _get_evals_formatted_time(evals: List[Evaluation]) -> str:
    max_time = _get_evals_time_in_ms(evals)
    return f'{max_time} ms'


def _print_solution_outcome(
    solution: Solution,
    evals: List[Evaluation],
    timeLimit: int,
    console: rich.console.Console,
    verification: VerificationLevel = VerificationLevel.NONE,
) -> bool:
    bad_verdicts = set()
    for eval in evals:
        if eval.result.outcome != Outcome.ACCEPTED:
            bad_verdicts.add(eval.result.outcome)

    unmatched_bad_verdicts = set(
        v for v in bad_verdicts if not solution.outcome.match(v)
    )
    matched_bad_verdicts = bad_verdicts - unmatched_bad_verdicts

    if unmatched_bad_verdicts:
        console.print('[error]FAILED[/error]', end=' ')
    else:
        console.print('[success]OK[/success]', end=' ')

    console.print(f'Expected: {solution.outcome}', end='')

    if unmatched_bad_verdicts:
        unmatched_bad_verdicts_names = set(v.name for v in unmatched_bad_verdicts)
        console.print(f', got: {" ".join(unmatched_bad_verdicts_names)}', end='')

    console.print()
    evals_time = _get_evals_time_in_ms(evals)
    if (
        not (matched_bad_verdicts - {Outcome.TIME_LIMIT_EXCEEDED})
        and verification.value >= VerificationLevel.FULL.value
        and evals_time > timeLimit
        and evals_time < timeLimit * 2
    ):
        console.print(
            '[yellow]WARNING[/yellow] The solution still passed in double TL.'
        )
    console.print(f'Time: {_get_evals_formatted_time(evals)}')
    return len(unmatched_bad_verdicts) == 0


def print_detailed_run_report(
    evals_per_solution: List[Dict[str, List[Evaluation]]],
    console: rich.console.Console,
    verification: environment.VerificationParam,
):
    pkg = package.find_problem_package_or_die()

    for group in pkg.testcases:
        console.print(f'[bold][status]{group.name}[/status][/bold]')

        table = rich.table.Table()

        for solution in pkg.solutions:
            table.add_column(f'[item]{solution.path}[/item]', justify='full')

        row_to_renderables: Dict[int, List[Any]] = collections.defaultdict(list)
        time_summary_row: List[str] = []

        for evals_per_group in evals_per_solution:
            evals = evals_per_group[group.name]
            max_time = _get_evals_formatted_time(evals)
            for i, eval in enumerate(evals):
                verdict = _get_testcase_markup_verdict(eval)
                time = _get_evals_formatted_time([eval])
                if time == max_time:
                    time = f'[underline][bold]{time}[/bold][/underline]'
                row_to_renderables[i].append(f'{verdict} {time}')

            time_summary_row.append('  ' + _get_evals_formatted_time(evals))

        for _, verdicts in sorted(row_to_renderables.items()):
            table.add_row(*verdicts)
        if len(row_to_renderables) > 1:
            # Only print footer row if there's more than one testcase.
            table.add_section()
            table.add_row(*time_summary_row)

        console.print(table)
    console.print()


def print_run_report(
    evals_per_solution: List[Dict[str, List[Evaluation]]],
    console: rich.console.Console,
    verification: environment.VerificationParam,
    detailed: bool = False,
) -> bool:
    pkg = package.find_problem_package_or_die()

    assert len(pkg.solutions) == len(evals_per_solution)

    if detailed:
        print_detailed_run_report(evals_per_solution, console, verification)

    ok = True
    for s, (solution, evals_per_group) in enumerate(
        zip(pkg.solutions, evals_per_solution)
    ):
        if not evals_per_group:
            continue
        solution_testdir = package.get_problem_runs_dir() / f'{s}'
        console.print(f'[item]{solution.path}[/item]', end=' ')
        console.print(f'({solution_testdir})')

        all_evals = []
        for group, evals in evals_per_group.items():
            all_evals.extend(evals)
            if detailed:
                continue
            console.print(f'[bold][status]{group}[/status][/bold]', end=' ')
            console.print(f'({_get_evals_formatted_time(evals)})', end=' ')
            for i, eval in enumerate(evals):
                console.print(f'{i}/', end='')
                console.print(_get_testcase_markup_verdict(eval), end=' ')
            console.print()

        cur_ok = _print_solution_outcome(
            solution,
            all_evals,
            pkg.timeLimit,
            console,
            verification=VerificationLevel(verification),
        )
        ok = ok and cur_ok
        console.print()

    return ok
