import pathlib
import shutil
from typing import Optional

import rich
import rich.prompt
import typer

from robox import console, utils
from robox.box.environment import get_environment_path
from robox.box.presets.schema import Preset
from robox.config import get_default_app_path

app = typer.Typer(no_args_is_help=True)


def find_preset_yaml(root: pathlib.Path = pathlib.Path()) -> Optional[pathlib.Path]:
    found = root / 'preset.rbx.yml'
    if found.exists():
        return found
    return None


def get_preset_yaml(root: pathlib.Path = pathlib.Path()) -> Preset:
    found = find_preset_yaml(root)
    if not found:
        console.console.print(
            f'[error]preset.rbx.yml not found in {root.absolute()}[/error]'
        )
        raise typer.Exit(1)
    return utils.model_from_yaml(Preset, found.read_text())


def get_preset_installation_path(name: str) -> pathlib.Path:
    return utils.get_app_path() / 'presets' / name


def _try_installing_from_resources(name: str) -> bool:
    rsrc_preset_path = get_default_app_path() / 'presets' / name
    if not rsrc_preset_path.exists():
        return False
    yaml_path = rsrc_preset_path / 'preset.rbx.yml'
    if not yaml_path.is_file():
        return False
    console.console.print(f'Installing preset [item]{name}[/item] from resources...')
    _install(rsrc_preset_path, force=True)
    return True


def get_installed_preset(name: str) -> Preset:
    installation_path = get_preset_installation_path(name) / 'preset.rbx.yml'
    if not installation_path.is_file():
        if not _try_installing_from_resources(name):
            console.console.print(
                f'[error]Preset [item]{name}[/item] is not installed.[/error]'
            )
            raise typer.Exit(1)
    return utils.model_from_yaml(Preset, installation_path.read_text())


def _install(root: pathlib.Path = pathlib.Path(), force: bool = False):
    preset = get_preset_yaml(root)

    console.console.print(f'Installing preset [item]{preset.name}[/item]...')

    if preset.env is not None:
        console.console.print('Copying environment file...')
        if get_environment_path(preset.name).exists():
            res = force or rich.prompt.Confirm.ask(
                f'Environment [item]{preset.name}[/item] already exists. Overwrite?',
                console=console.console,
            )
            if not res:
                raise typer.Exit(1)

        shutil.copyfile(str(root / preset.env), get_environment_path(preset.name))

    console.console.print('Copying preset folder...')
    installation_path = get_preset_installation_path(preset.name)
    installation_path.parent.mkdir(parents=True, exist_ok=True)
    if installation_path.exists():
        res = force or rich.prompt.Confirm.ask(
            f'Preset [item]{preset.name}[/item] is already installed. Overwrite?',
            console=console.console,
        )
        if not res:
            raise typer.Exit(1)
    shutil.rmtree(str(installation_path), ignore_errors=True)
    shutil.copytree(str(root), str(installation_path))
    shutil.rmtree(str(installation_path / 'build'), ignore_errors=True)
    shutil.rmtree(str(installation_path / '.box'), ignore_errors=True)


@app.command('install', help='Install preset from current directory.')
def install():
    _install()


@app.callback()
def callback():
    pass
