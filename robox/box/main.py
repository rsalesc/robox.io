# flake8: noqa
from os import environ
from gevent import monkey

monkey.patch_all()

import pathlib
import shutil
from typing import Annotated, Optional

import rich
import rich.prompt
import typer

from robox import annotations, config, console, utils
from robox.box import (
    builder,
    creation,
    download,
    environment,
    package,
    compile,
    presets,
    stresses,
)
from robox.box.contest import main as contest
from robox.box.environment import VerificationLevel, get_environment_path
from robox.box.packaging import main as packaging
from robox.box.solutions import (
    convert_list_of_solution_evaluations_to_dict,
    _get_report_skeleton,
    print_run_report,
    run_and_print_interactive_solutions,
    run_solutions,
)
from robox.box.statements import build_statements

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)
app.add_typer(
    build_statements.app,
    name='statements, st',
    cls=annotations.AliasGroup,
    help='Manage statements.',
)
app.add_typer(
    download.app,
    name='download',
    cls=annotations.AliasGroup,
    help='Download an asset from supported repositories.',
)
app.add_typer(
    presets.app, name='presets', cls=annotations.AliasGroup, help='Manage presets.'
)
app.add_typer(
    packaging.app,
    name='package, pkg',
    cls=annotations.AliasGroup,
    help='Build problem packages.',
)
app.add_typer(
    contest.app, name='contest', cls=annotations.AliasGroup, help='Contest management.'
)
app.add_typer(
    compile.app, name='compile', cls=annotations.AliasGroup, help='Compile assets.'
)


@app.command('edit, e', help='Open problem.rbx.yml in your default editor.')
def edit():
    console.console.print('Opening problem definition in editor...')
    # Call this function just to raise exception in case we're no in
    # a problem package.
    package.find_problem()
    config.open_editor(package.find_problem_yaml() or pathlib.Path())


@app.command('build, b', help='Build all tests for the problem.')
def build(verification: environment.VerificationParam):
    builder.build(verification=verification)


@app.command('verify, v', help='Build and verify all the tests for the problem.')
def verify(verification: environment.VerificationParam):
    if not builder.verify(verification=verification):
        console.console.print('[error]Verification failed, check the report.[/error]')


@app.command('run, r', help='Build and run solution(s).')
def run(
    verification: environment.VerificationParam,
    solution: Annotated[
        Optional[str],
        typer.Argument(
            help='Path to solution to run. If not specified, will run all solutions.'
        ),
    ] = None,
    check: bool = typer.Option(
        True,
        '--nocheck',
        flag_value=False,
        help='Whether to not build outputs for tests and run checker.',
    ),
    detailed: bool = typer.Option(
        False,
        '--detailed',
        '-d',
        help='Whether to print a detailed view of the tests using tables.',
    ),
):
    main_solution = package.get_main_solution()
    if check and main_solution is None:
        console.console.print(
            '[warning]No main solution found, running without checkers.[/warning]'
        )
        check = False

    builder.build(verification=verification, output=check)

    with utils.StatusProgress('Running solutions...') as s:
        tracked_solutions = None
        if solution:
            tracked_solutions = {solution}
        solution_result = run_solutions(
            progress=s,
            tracked_solutions=tracked_solutions,
            check=check,
            group_first=detailed,
        )

    console.console.print()
    console.console.rule('[status]Run report[/status]', style='status')
    print_run_report(
        solution_result,
        console.console,
        verification,
        detailed=detailed,
    )


@app.command(
    'irun, ir', help='Build and run solution(s) by passing testcases in the CLI.'
)
def irun(
    verification: environment.VerificationParam,
    solution: Annotated[
        Optional[str],
        typer.Argument(
            help='Path to solution to run. If not specified, will run all solutions.'
        ),
    ] = None,
    check: bool = typer.Option(
        True,
        '--nocheck',
        flag_value=False,
        help='Whether to not build outputs for tests and run checker.',
    ),
):
    main_solution = package.get_main_solution()
    if check and main_solution is None:
        console.console.print(
            '[warning]No main solution found, running without checkers.[/warning]'
        )
        check = False

    tracked_solutions = None
    if solution:
        tracked_solutions = {solution}
    run_and_print_interactive_solutions(
        tracked_solutions=tracked_solutions,
        check=check,
    )


@app.command('create, c', help='Create a new problem package.')
def create(
    name: str,
    preset: Annotated[
        Optional[str], typer.Option(help='Preset to use when creating the problem.')
    ] = None,
):
    if preset is not None:
        creation.create(name, preset=preset)
        return
    creation.create(name)


@app.command('stress', help='Run a stress test.')
def stress(
    name: str,
    solution: Annotated[
        Optional[str],
        typer.Option(
            '--solution',
            '-s',
            help='Path to solution to run. If not specified, will run all solutions.',
        ),
    ] = None,
    generator_args: Annotated[
        Optional[str],
        typer.Option(
            '--generator',
            '-g',
            help='Run generator [name] with these args.',
        ),
    ] = None,
    timeout: Annotated[
        int, typer.Option(help='For how many seconds to run the stress test.')
    ] = 10,
    findings: Annotated[
        int, typer.Option(help='How many breaking tests to look for.')
    ] = 1,
    check: bool = typer.Option(
        True,
        '--nocheck',
        flag_value=False,
        help='Whether to not build outputs for tests and run checker.',
    ),
):
    if solution and not generator_args:
        console.console.print(
            '[error]Options --generator/-g and --solution/-s should be specified together.'
        )
        raise typer.Exit(1)

    with utils.StatusProgress('Running stress...') as s:
        report = stresses.run_stress(
            name,
            timeout,
            solution=solution,
            args=generator_args,
            findingsLimit=findings,
            progress=s,
            check=check,
        )

    stresses.print_stress_report(report)

    if not report.findings:
        return

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
            # Reassign mutable object before saving.
            testgroup.generators = testgroup.generators + [
                f.generator for f in report.findings
            ]
            package.save_package()
            console.console.print(
                f'Added [item]{len(report.findings)}[/item] tests to test group [item]{testgroup.name}[/item].'
            )
        except typer.Exit:
            continue
        break


@app.command('environment, env', help='Set or show the current box environment.')
def environment_command(env: Annotated[Optional[str], typer.Argument()] = None):
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


@app.command(
    'activate',
    help='Activate the environment of the current preset used by the package.',
)
def activate():
    preset_lock = presets.get_preset_lock()
    if preset_lock is None:
        console.console.print(
            '[warning]No configured preset to be activated for this package.[/warning]'
        )
        raise typer.Exit(1)

    preset = presets.get_installed_preset_or_null(preset_lock.preset_name)
    if preset is None:
        if preset_lock.uri is None:
            console.console.print(
                '[error]Preset is not installed. Install it manually, or specify a URI in [item].preset-lock.yml[/item].[/error]'
            )
            raise
        presets.install(preset_lock.uri)

    preset = presets.get_installed_preset(preset_lock.preset_name)
    if preset.env is not None:
        environment_command(preset.name)

    console.console.print(f'[success]Preset [item]{preset.name}[/item] is activated.')


@app.command('clear, clean', help='Clears cache and build directories.')
def clear():
    console.console.print('Cleaning cache and build directories...')
    shutil.rmtree('.box', ignore_errors=True)
    shutil.rmtree('build', ignore_errors=True)


@app.callback()
def callback():
    pass
