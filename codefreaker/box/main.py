import pathlib
import shutil
from typing import Annotated, Optional

import rich
import rich.prompt
import typer

from codefreaker import annotations, config, console, utils
from codefreaker.box import package, stresses
from codefreaker.box.environment import get_environment_path
from codefreaker.box.generators import (
    generate_outputs_for_testcases,
    generate_testcases,
)
from codefreaker.box.solutions import print_run_report, run_solutions
from codefreaker.box.statements import build_statements
from codefreaker.box.validators import print_validation_report, validate_testcases

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)
app.add_typer(build_statements.app, name='statements', cls=annotations.AliasGroup)


@app.command('edit')
def edit():
    console.console.print('Opening problem definition in editor...')
    # Call this function just to raise exception in case we're no in
    # a problem package.
    package.find_problem()
    config.open_editor(package.find_problem_yaml() or pathlib.Path())


@app.command('build, b')
def build(verify: bool = True):
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

    console.console.print('[success]Problem built successfully![/success]')


@app.command('run')
def run(solution: Annotated[Optional[str], typer.Argument()] = None):
    build()

    with utils.StatusProgress('Running solutions...') as s:
        tracked_solutions = None
        if solution:
            tracked_solutions = {solution}
        evals_per_solution = run_solutions(
            s,
            tracked_solutions=tracked_solutions,
        )

    console.console.print()
    console.console.rule('[status]Run report[/status]', style='status')
    print_run_report(evals_per_solution, console.console)


@app.command('stress')
def stress(
    name: str,
    timeout: Annotated[int, typer.Option()] = 10,
    findings: Annotated[int, typer.Option()] = 1,
):
    with utils.StatusProgress('Running stress...') as s:
        finding_list = stresses.run_stress(
            name, timeout, findingsLimit=findings, progress=s
        )

    stresses.print_stress_report(finding_list)

    # Add found tests.
    res = rich.prompt.Confirm.ask(
        'Do you want to add the tests that were found to a test group?',
        console=console.console,
    )
    if not res:
        return
    testgroup = None
    while testgroup is None or testgroup:
        testgroup = rich.prompt.Prompt.ask(
            'Enter the name of the test group, or empty to cancel',
            console=console.console,
        )
        if not testgroup:
            break
        try:
            testgroup = package.get_testgroup(testgroup)
            testgroup.generators.extend(f.generator for f in finding_list)
            package.save_package()
            console.console.print(
                f'Added [item]{len(finding_list)}[/item] tests to test group [item]{testgroup.name}[/item].'
            )
        except typer.Exit:
            continue
        break


@app.command('environment, env')
def environment(env: Annotated[Optional[str], typer.Argument()] = None):
    if env is None:
        cfg = config.get_config()
        console.console.print(f'Current environment: [item]{cfg.boxEnvironment}[/item]')
        return
    if not get_environment_path(env).is_file():
        console.console.print(
            f'[error]Environment [item]{env}[/item] does not exist.[/error]'
        )
        raise typer.Exit(1)

    cfg = config.get_config()
    if env == cfg.boxEnvironment:
        console.console.print(
            f'Environment is already set to [item]{env}[/item].',
        )
        return
    console.console.print(
        f'Changing box environment from [item]{cfg.boxEnvironment}[/item] to [item]{env}[/item]...'
    )
    cfg.boxEnvironment = env
    config.save_config(cfg)

    # Also clear cache when changing environments.
    clear()


@app.command('clear, clean')
def clear():
    console.console.print('Cleaning cache and build directories...')
    shutil.rmtree('.box', ignore_errors=True)
    shutil.rmtree('build', ignore_errors=True)


@app.callback()
def callback():
    pass
