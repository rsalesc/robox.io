import pathlib
import tempfile
from typing import Type

import typer

from robox import annotations, console
from robox.box import builder, package
from robox.box.package import get_build_path
from robox.box.packaging.boca.packager import BocaPackager
from robox.box.packaging.packager import BasePackager, BuiltStatement
from robox.box.packaging.polygon.packager import PolygonPackager
from robox.box.statements.build_statements import build_statement

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


def run_packager(
    packager_cls: Type[BasePackager],
    verification: annotations.VerificationLevel,
):
    builder.build(verification=verification)

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

    packager.built_statements = built_statements
    console.console.print(f'Packaging problem for [item]{packager.name()}[/item]...')

    with tempfile.TemporaryDirectory() as td:
        packager.package(get_build_path(), pathlib.Path(td))

    console.console.print(
        f'[success]Problem packaged for [item]{packager.name()}[/item]![/success]'
    )


@app.command('polygon')
def polygon(
    verification: annotations.VerificationLevel,
):
    run_packager(PolygonPackager, verification=verification)


@app.command('boca')
def boca(
    verification: annotations.VerificationLevel,
):
    run_packager(BocaPackager, verification=verification)
