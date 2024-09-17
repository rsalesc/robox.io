import pathlib
import shutil
from typing import Annotated, Optional

import typer

from robox import console
from robox.box import presets
from robox.box.presets.fetch import get_preset_fetch_info


def create(
    name: Annotated[
        str,
        typer.Argument(
            help='The name of the problem package to create. This will also be the name of the folder.'
        ),
    ],
    preset: Annotated[
        str,
        typer.Option(
            help='Which preset to use to create this package. Can be a named of an already installed preset, or an URI, in which case the preset will be downloaded.'
        ),
    ] = 'default',
    path: Optional[pathlib.Path] = None,
):
    console.console.print(f'Creating new problem [item]{name}[/item]...')

    fetch_info = get_preset_fetch_info(preset)
    if fetch_info is None:
        console.console.print(
            f'[error]Invalid preset name/URI [item]{preset}[/item].[/error]'
        )
        raise typer.Exit(1)

    if fetch_info.fetch_uri is not None:
        preset = presets.install_from_remote(fetch_info)

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

    presets.generate_lock(preset, root=dest_path)
