from typing import List

import typer

from codefreaker import annotations, console
from codefreaker.box import package
from codefreaker.box.schema import Statement
from codefreaker.box.statement_builders import (
    BUILDER_LIST,
    StatementBuilder,
    StatementBuilderInput,
)

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


def get_builder(name: str) -> StatementBuilder:
    candidates = [builder for builder in BUILDER_LIST if builder.name() == name]
    if not candidates:
        console.console.print(
            f'[error]No statement builder found with name [name]{name}[/name][/error]'
        )
        raise typer.Exit(1)
    return candidates[0]


def get_builders(statement: Statement) -> List[StatementBuilder]:
    last_output = statement.type
    builders: List[StatementBuilder] = []
    for step in statement.pipeline:
        builder = get_builder(step.type)
        if builder.input_type() != last_output:
            console.console.print(
                f'[error]Invalid pipeline step: [item]{builder.name()}[/item][/error]'
            )
            raise typer.Exit(1)
        builders.append(builder)
        last_output = builder.output_type()

    return builders


def build_statement(statement: Statement):
    builders = get_builders(statement)
    last_output = statement.type
    last_content = statement.path.read_bytes()
    for builder in builders:
        output = builder.build(
            StatementBuilderInput(id=statement.path.name, content=last_content),
            verbose=False,
        )
        last_output = builder.output_type()
        last_content = output.content

    statement_path = (
        package.get_build_path()
        / f'{statement.path.stem}{last_output.get_file_suffix()}'
    )
    statement_path.parent.mkdir(parents=True, exist_ok=True)
    statement_path.write_bytes(last_content)
    console.console.print(
        f'Statement built successfully for language '
        f'[item]{statement.language}[/item] at '
        f'[item]{statement_path}[/item].'
    )


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
