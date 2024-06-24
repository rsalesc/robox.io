import pathlib

import typer

from codefreaker import annotations, console
from codefreaker.box import package
from codefreaker.box.schema import Statement
from codefreaker.box.statement_builders import BUILDER_LIST, StatementBuilder

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


def get_builder(statement: Statement) -> StatementBuilder:
    candidates = [
        builder for builder in BUILDER_LIST if builder.should_handle(statement)
    ]
    if not candidates:
        console.console.print(
            f'No statement builder found for {statement.params.type}', style='error'
        )
        raise typer.Exit(1)
    return candidates[0]


def build_statement(statement: Statement):
    builder = get_builder(statement)
    while builder is not None:
        res = builder.build(statement)
        if isinstance(res, StatementBuilder):
            builder = res
        if isinstance(res, pathlib.Path):
            console.console.print(f'Statement built at [item]{res}[/item]')
            break


@app.command('build')
def build(language: str):
    pkg = package.find_problem_package_or_die()
    candidates_for_lang = [st for st in pkg.statements if st.language == language]
    if not candidates_for_lang:
        console.console.print(
            f'[error]No statement found for language [item]{language}[/item].[/error]',
        )
        raise typer.Exit(1)

    build_statement(candidates_for_lang[0])


@app.callback()
def callback():
    pass
