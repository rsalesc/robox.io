import pathlib
import shutil
from typing import Optional

import typer

from robox import console
from robox.box import presets


def create(
    name: str, preset: Optional[str] = None, path: Optional[pathlib.Path] = None
):
    console.console.print(f'Creating new problem [item]{name}[/item]...')

    preset = preset or 'default'
    preset_cfg = presets.get_installed_preset(preset)

    problem_path = (
        presets.get_preset_installation_path(preset) / preset_cfg.problem
        if preset_cfg.problem is not None
        else presets.get_preset_installation_path('default') / 'problem'
    )

    if not problem_path.is_dir():
        console.console.print(
            f'[error]Problem template [item]{problem_path}[/item] does not exist.[/error]'
        )
        raise typer.Exit(1)

    dest_path = path or pathlib.Path(name)

    if dest_path.exists():
        console.console.print(
            f'[error]Directory [item]{dest_path}[/item] already exists.[/error]'
        )
        raise typer.Exit(1)

    shutil.copytree(str(problem_path), str(dest_path))
    shutil.rmtree(str(dest_path / 'build'), ignore_errors=True)
    shutil.rmtree(str(dest_path / '.box'), ignore_errors=True)
