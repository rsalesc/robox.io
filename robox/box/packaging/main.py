import pathlib
import tempfile
from typing import Type

import typer

from robox import annotations, console
from robox.box import builder, environment, package
from robox.box.package import get_build_path
from robox.box.packaging.boca.packager import BocaPackager
from robox.box.packaging.packager import BasePackager, BuiltStatement
from robox.box.packaging.polygon.packager import PolygonPackager
from robox.box.statements.build_statements import build_statement

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


def run_packager(
    packager_cls: Type[BasePackager],
    verification: environment.VerificationParam,
) -> pathlib.Path:
    if not builder.verify(verification=verification):
        console.console.print(
            '[error]Build or verification failed, check the report.[/error]'
        )
        raise typer.Exit(1)

    pkg = package.find_problem_package_or_die()
    packager = packager_cls()

    statement_types = packager.statement_types()
    built_statements = []

    for statement_type in statement_types:
        languages = packager.languages()
        for language in languages:
            statement = packager.get_statement_for_language(language)
            statement_path = build_statement(statement, pkg, statement_type)
            built_statements.append(
                BuiltStatement(statement, statement_path, statement_type)
            )

    console.console.print(f'Packaging problem for [item]{packager.name()}[/item]...')

    with tempfile.TemporaryDirectory() as td:
        result_path = packager.package(
            get_build_path(), pathlib.Path(td), built_statements
        )

    console.console.print(
        f'[success]Problem packaged for [item]{packager.name()}[/item]![/success]'
    )
    console.console.print(f'Package was saved at [item]{result_path}[/item].')
    return result_path


@app.command('polygon', help='Build a package for Polygon.')
def polygon(
    verification: environment.VerificationParam,
):
    run_packager(PolygonPackager, verification=verification)


@app.command('boca', help='Build a package for BOCA.')
def boca(
    verification: environment.VerificationParam,
):
    run_packager(BocaPackager, verification=verification)
