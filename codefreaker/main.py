from typing import Optional
import typer
import rich
import pathlib

from . import clone as clone_pkg
from . import config
from . import metadata
from . import hydration
from . import test

app = typer.Typer(no_args_is_help=True)
app.add_typer(config.app, name='config')
app.add_typer(test.app, name='test')

@app.command()
def clone(lang: Optional[str] = None):
  clone_pkg.main(lang=lang)

@app.callback()
def callback():
  pass