import pathlib
import shutil
from typing import Annotated, Optional

import typer

from robox import annotations, console
from robox.box import presets

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


@app.command('create', help='Create a new contest package.')
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
