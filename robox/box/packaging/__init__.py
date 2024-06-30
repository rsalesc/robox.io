import pathlib
import tempfile
from typing import Type

import typer

from robox import annotations, console
from robox.box.package import get_build_path
from robox.box.packaging.packager import BasePackager
from robox.box.packaging.polygon.packager import PolygonPackager

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


def run_packager(packager_cls: Type[BasePackager]):
    packager = packager_cls()

    console.console.print(f'Packaging problem for [item]{packager.name()}[/item]...')
    with tempfile.TemporaryDirectory() as td:
        packager.package(get_build_path(), pathlib.Path(td))

    console.console.print(
        f'[success]Problem packaged for [item]{packager.name()}[/item]![/success]'
    )


@app.command('polygon')
def polygon():
    run_packager(PolygonPackager)
