import pathlib
import typing
from typing import Annotated, Dict, List, Optional, Tuple

import typer

from codefreaker import annotations, console
from codefreaker.box import environment, package
from codefreaker.box.schema import Package
from codefreaker.box.statements.builders import (
    BUILDER_LIST,
    StatementBuilder,
    StatementBuilderInput,
    StatementCodeLanguage,
)
from codefreaker.box.statements.schema import PipelineStep, Statement, StatementType

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


def _get_environment_languages_for_statement() -> List[StatementCodeLanguage]:
    env = environment.get_environment()

    res = []
    for language in env.languages:
        cmd = ''
        compilation_cfg = environment.get_compilation_config(language.name)
        cmd = ' & '.join(compilation_cfg.commands or [])
        if not cmd:
            execution_cfg = environment.get_execution_config(language.name)
            cmd = execution_cfg.command

        res.append(
            StatementCodeLanguage(
                name=language.readable_name or language.name, command=cmd or ''
            )
        )

    return res


def get_builder(name: str) -> StatementBuilder:
    candidates = [builder for builder in BUILDER_LIST if builder.name() == name]
    if not candidates:
        console.console.print(
            f'[error]No statement builder found with name [name]{name}[/name][/error]'
        )
        raise typer.Exit(1)
    return candidates[0]


def get_implicit_builders(
    input_type: StatementType, output_type: StatementType
) -> Optional[List[StatementBuilder]]:
    par: Dict[StatementType, Optional[StatementBuilder]] = {input_type: None}

    def _iterate() -> bool:
        nonlocal par
        for builder in BUILDER_LIST:
            u = builder.input_type()
            if u not in par:
                continue
            v = builder.output_type()
            if v in par:
                continue
            par[v] = builder
            return True
        return False

    while _iterate() and output_type not in par:
        pass

    if output_type not in par:
        return None

    res = []
    cur = output_type
    while par[cur] is not None:
        res.append(par[cur])
        cur = typing.cast(StatementBuilder, par[cur]).input_type()

    return list(reversed(res))


def get_builders(
    statement: Statement, output_type: Optional[StatementType]
) -> List[Tuple[StatementBuilder, PipelineStep]]:
    last_output = statement.type
    builders: List[Tuple[StatementBuilder, PipelineStep]] = []
    for step in statement.pipeline:
        builder = get_builder(step.type)
        if builder.input_type() != last_output:
            console.console.print(
                f'[error]Invalid pipeline step: [item]{builder.name()}[/item][/error]'
            )
            raise typer.Exit(1)
        builders.append((builder, step))
        last_output = builder.output_type()

    if output_type is not None and last_output != output_type:
        console.console.print(
            'Implicitly adding statement builders to convert statement'
            f'from [item]{last_output}[/item] to [item]{output_type}[/item]...'
        )
        implicit_builders = get_implicit_builders(last_output, output_type)
        if implicit_builders is None:
            console.console.print(
                f'[error]Cannot convert statement [item]{statement.path}[/item] '
                f'from [item]{last_output}[/item] '
                f'to specified output type [item]{output_type}[/item].[/error]'
            )
            raise typer.Exit(1)
        builders.extend(
            (builder, builder.default_params()) for builder in implicit_builders
        )

    return builders


def _get_relative_assets(
    statement_path: pathlib.Path,
    assets: List[pathlib.Path],
) -> List[Tuple[pathlib.Path, pathlib.Path]]:
    res = []
    for asset in assets:
        if not asset.is_file() or not asset.resolve().is_relative_to(
            statement_path.resolve().parent
        ):
            console.console.print(
                f'[error]Asset [item]{asset}[/item] is not relative to your statement.[/error]'
            )
            raise typer.Exit(1)

        res.append(
            (asset, asset.resolve().relative_to(statement_path.resolve().parent))
        )

    return res


def build_statement(
    statement: Statement, pkg: Package, output_type: Optional[StatementType] = None
):
    if not statement.path.is_file():
        console.console.print(
            f'[error]Statement file [item]{statement.path}[/item] does not exist.[/error]'
        )
        raise typer.Exit(1)
    builders = get_builders(statement, output_type)
    last_output = statement.type
    last_content = statement.path.read_bytes()
    for builder, params in builders:
        assets = _get_relative_assets(
            statement.path, statement.assets
        ) + builder.inject_assets(params)
        output = builder.build(
            StatementBuilderInput(
                id=statement.path.name,
                languages=_get_environment_languages_for_statement(),
                package=pkg,
                statement=statement,
                content=last_content,
                params=params,
                assets=assets,
            ),
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
def build(
    languages: Annotated[Optional[List[str]], typer.Option(default_factory=list)],
    output: Annotated[
        Optional[StatementType], typer.Option(case_sensitive=False)
    ] = None,
):
    pkg = package.find_problem_package_or_die()
    candidate_languages = languages
    if not candidate_languages:
        candidate_languages = sorted(set([st.language for st in pkg.statements]))

    for language in candidate_languages:
        candidates_for_lang = [st for st in pkg.statements if st.language == language]
        if not candidates_for_lang:
            console.console.print(
                f'[error]No statement found for language [item]{language}[/item].[/error]',
            )
            raise typer.Exit(1)

        build_statement(candidates_for_lang[0], pkg, output_type=output)


@app.callback()
def callback():
    pass
