from typing import Optional
import typer
import rich
import pathlib

from . import clone as clone_pkg
from . import config
from . import metadata
from . import hydration

app = typer.Typer(no_args_is_help=True)
app.add_typer(config.app, name='config')

@app.command()
def clone(lang: Optional[str] = None):
  clone_pkg.main(lang=lang)

@app.command()
def hydrate(problem: Optional[str] = None):
  hydration.main(problem=problem)

@app.callback()
def callback():
  pass