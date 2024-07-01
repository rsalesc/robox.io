from robox import console, utils
from robox.box.generators import generate_outputs_for_testcases, generate_testcases
from robox.box.validators import print_validation_report, validate_testcases


def build(verify: bool = True) -> None:
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

    if verify:
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
