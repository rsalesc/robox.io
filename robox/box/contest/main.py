import pathlib
import shutil
from typing import Annotated, Optional

import typer

from robox import annotations, console, utils
from robox.box import creation, presets
from robox.box.contest import statements
from robox.box.contest.contest_package import (
    find_contest,
    find_contest_package_or_die,
    find_contest_yaml,
    save_contest,
)
from robox.box.contest.schema import ContestProblem
from robox.box.schema import Package
from robox.config import open_editor

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)
app.add_typer(
    statements.app,
    name='statements',
    cls=annotations.AliasGroup,
    help='Manage contest-level statements.',
)


@app.command('create, c', help='Create a new contest package.')
def create(
    name: str,
    preset: Annotated[
        Optional[str], typer.Option(help='Preset to use when creating the contest.')
    ] = None,
):
    console.console.print(f'Creating new contest [item]{name}[/item]...')

    preset = preset or 'default'
    preset_cfg = presets.get_installed_preset(preset)

    contest_path = (
        presets.get_preset_installation_path(preset) / preset_cfg.contest
        if preset_cfg.contest is not None
        else presets.get_preset_installation_path('default') / 'contest'
    )

    if not contest_path.is_dir():
        console.console.print(
            f'[error]Contest template [item]{contest_path}[/item] does not exist.[/error]'
        )
        raise typer.Exit(1)

    dest_path = pathlib.Path(name)

    if dest_path.exists():
        console.console.print(
            f'[error]Directory [item]{dest_path}[/item] already exists.[/error]'
        )
        raise typer.Exit(1)

    shutil.copytree(str(contest_path), str(dest_path))


@app.command('edit, e', help='Open contest.rbx.yml in your default editor.')
def edit():
    console.console.print('Opening contest definition in editor...')
    # Call this function just to raise exception in case we're no in
    # a problem package.
    find_contest()
    open_editor(find_contest_yaml() or pathlib.Path())


@app.command('add, a', help='Add new problem to contest.')
def add(name: str, short_name: str, preset: Optional[str] = None):
    utils.validate_field(ContestProblem, 'short_name', short_name)
    utils.validate_field(Package, 'name', name)

    if short_name in [p.short_name for p in find_contest_package_or_die().problems]:
        console.console.print(
            f'[error]Problem [item]{short_name}[/item] already exists in contest.[/error]',
        )
        raise typer.Exit(1)

    creation.create(name, preset=preset, path=pathlib.Path(short_name))

    contest = find_contest_package_or_die()
    contest.problems.append(
        ContestProblem(short_name=short_name, path=pathlib.Path(short_name))
    )

    contest.problems.sort(key=lambda p: p.short_name)
    save_contest(contest)
    console.console.print(f'Problem [item]{short_name}[/item] added to contest.')
