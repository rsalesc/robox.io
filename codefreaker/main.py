import typer
import rich

from . import clone as clone_pkg

app = typer.Typer()

@app.command()
def clone():
  clone_pkg.main()

@app.callback()
def callback():
  pass