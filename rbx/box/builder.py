from typing import Optional, Set

from rbx import console, utils
from rbx.box import environment, package
from rbx.box.environment import VerificationLevel
from rbx.box.generators import generate_outputs_for_testcases, generate_testcases
from rbx.box.solutions import (
    is_fast,
    print_run_report,
    run_solutions,
)
from rbx.box.validators import print_validation_report, validate_testcases


def build(
    verification: environment.VerificationParam,
    groups: Optional[Set[str]] = None,
    output: bool = True,
) -> None:
    with utils.StatusProgress(
        'Building testcases...',
        'Built [item]{processed}[/item] testcases...',
        keep=True,
    ) as s:
        generate_testcases(s, groups=groups)

    with utils.StatusProgress(
        'Building outputs for testcases...',
        'Built [item]{processed}[/item] outputs...',
        keep=True,
    ) as s:
        if output:
            generate_outputs_for_testcases(s, groups=groups)

    if verification > 0:
        with utils.StatusProgress(
            'Validating testcases...',
            'Validated [item]{processed}[/item] testcases...',
            keep=True,
        ) as s:
            infos = validate_testcases(s, groups=groups)
            print_validation_report(infos)

    console.console.print(
        '[success]Problem built.[/success] '
        '[warning]Check the output for verification errors![/warning]'
    )


def verify(verification: environment.VerificationParam) -> bool:
    build(verification=verification)

    if verification < VerificationLevel.FAST_SOLUTIONS.value:
        return True

    tracked_solutions = None
    if verification < VerificationLevel.ALL_SOLUTIONS.value:
        pkg = package.find_problem_package_or_die()

        tracked_solutions = {
            str(solution.path) for solution in pkg.solutions if is_fast(solution)
        }

    with utils.StatusProgress('Running solutions...') as s:
        solution_result = run_solutions(
            progress=s,
            tracked_solutions=tracked_solutions,
            verification=VerificationLevel(verification),
        )

    console.console.print()
    console.console.rule('[status]Run report[/status]', style='status')
    return print_run_report(
        solution_result,
        console.console,
        verification,
    )
