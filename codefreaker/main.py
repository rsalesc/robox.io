from typing import Optional
import typer
import rich
import pathlib

from .console import console
from . import annotations
from . import clone as clone_pkg
from . import config
from . import metadata
from . import hydration
from . import test
from . import create as create_pkg

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)
app.add_typer(config.app, name="config, cfg", cls=annotations.AliasGroup)
app.add_typer(test.app, name="test, t", cls=annotations.AliasGroup)


@app.command("clone, c")
def clone(lang: annotations.Language):
    clone_pkg.main(lang=lang)


@app.command("new, n")
def new(
    name: str,
    language: annotations.Language,
    timelimit: annotations.Timelimit = 1000,
    memorylimit: annotations.Memorylimit = 256,
):
    create_pkg.main(name, language, timelimit, memorylimit)


@app.callback()
def callback():
    pass
