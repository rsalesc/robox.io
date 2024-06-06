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

app = typer.Typer(no_args_is_help=True)
app.add_typer(config.app, name='config')
app.add_typer(test.app, name='test')

@app.command()
def clone(lang: Optional[str] = None):
  clone_pkg.main(lang=lang)

@app.command()
def create(name: str,
           language: annotations.Language,
           timelimit: annotations.Timelimit = 1000,
           memorylimit: annotations.Memorylimit = 256):
  create_pkg.main(name, language, timelimit, memorylimit)

@app.callback()
def callback():
  pass