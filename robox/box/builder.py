from robox import console, utils
from robox.box import environment
from robox.box.environment import VerificationLevel
from robox.box.generators import generate_outputs_for_testcases, generate_testcases
from robox.box.solutions import print_run_report, run_solutions
from robox.box.validators import print_validation_report, validate_testcases


def build(verification: environment.VerificationParam) -> None:
    with utils.StatusProgress(
        'Building testcases...',
        'Built [item]{processed}[/item] testcases...',
        keep=True,
    ) as s:
        generate_testcases(s)

    with utils.StatusProgress(
        'Building outputs for testcases...',
        'Built [item]{processed}[/item] outputs...',
        keep=True,
    ) as s:
        generate_outputs_for_testcases(s)

    if verification.value > 0:
        with utils.StatusProgress(
            'Validating testcases...',
            'Validated [item]{processed}[/item] testcases...',
            keep=True,
        ) as s:
            infos = validate_testcases(s)
            print_validation_report(infos)

    console.console.print(
        '[success]Problem built.[/success] '
        '[warning]Check the output for verification errors![/warning]'
    )


def verify(verification: environment.VerificationParam) -> bool:
    build(verification=verification)

    if verification.value < VerificationLevel.FAST_SOLUTIONS.value:
        return True

    with utils.StatusProgress('Running solutions...') as s:
        evals_per_solution = run_solutions(
            s,
        )

    console.console.print()
    console.console.rule('[status]Run report[/status]', style='status')
    return print_run_report(evals_per_solution, console.console, verification)
