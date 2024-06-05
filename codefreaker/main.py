from typing import Optional
import typer
import rich

from . import clone as clone_pkg
from . import config

app = typer.Typer(no_args_is_help=True)
app.add_typer(config.app, name='config')


@app.command()
def clone(lang: Optional[str] = None):
  clone_pkg.main(lang=lang)

@app.callback()
def callback():
  pass