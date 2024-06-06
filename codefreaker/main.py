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
from . import edit as edit_pkg

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)
app.add_typer(
    config.app,
    name="config, cfg",
    cls=annotations.AliasGroup,
    help="Manage the configuration of the tool.",
)
app.add_typer(
    test.app,
    name="test, t",
    cls=annotations.AliasGroup,
    help="Commands to manage the testcases of a problem.",
)


@app.command("clone, c")
def clone(lang: annotations.Language):
    """
    Clones by waiting for a set of problems to be sent through Competitive Companion.
    """
    clone_pkg.main(lang=lang)


@app.command("new, n")
def new(
    name: str,
    language: annotations.Language,
    timelimit: annotations.Timelimit = 1000,
    memorylimit: annotations.Memorylimit = 256,
):
    """
    Create a new problem from scratch.
    """
    create_pkg.main(name, language, timelimit, memorylimit)


@app.command("edit, e")
def edit(problem: str, language: annotations.LanguageWithDefault = None):
    edit_pkg.main(problem, language)


@app.callback()
def callback():
    pass
