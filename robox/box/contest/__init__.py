import typer

from robox import annotations

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)
