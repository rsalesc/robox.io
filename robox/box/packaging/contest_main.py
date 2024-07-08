import pathlib
import tempfile
from typing import Type

import typer

from robox import annotations, console, utils
from robox.box import environment, package
from robox.box.contest import build_contest_statements, contest_package, contest_utils
from robox.box.packaging.main import run_packager
from robox.box.packaging.packager import (
    BaseContestPackager,
    BasePackager,
    BuiltContestStatement,
    BuiltProblemPackage,
)
from robox.box.packaging.polygon.packager import PolygonContestPackager, PolygonPackager

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


def run_contest_packager(
    contest_packager_cls: Type[BaseContestPackager],
    packager_cls: Type[BasePackager],
    verification: environment.VerificationParam,
):
    contest = contest_package.find_contest_package_or_die()

    # Build problem-level packages.
    built_packages = []
    for problem in contest.problems:
        console.console.print(
            f'Processing problem [item]{problem.short_name}[/item]...'
        )
        with utils.new_cd(problem.get_path()):
            contest_utils.clear_package_cache()
            package_path = run_packager(packager_cls, verification=verification)
            built_packages.append(
                BuiltProblemPackage(
                    path=problem.get_path() / package_path,
                    package=package.find_problem_package_or_die(),
                    problem=problem,
                )
            )

    # Build statements.
    packager = contest_packager_cls()
    statement_types = packager.statement_types()
    built_statements = []

    for statement_type in statement_types:
        languages = packager.languages()
        for language in languages:
            statement = packager.get_statement_for_language(language)
            statement_path = build_contest_statements.build_statement(
                statement, contest, statement_type
            )
            built_statements.append(
                BuiltContestStatement(statement, statement_path, statement_type)
            )

    console.console.print(f'Packaging contest for [item]{packager.name()}[/item]...')

    # Build contest-level package.
    with tempfile.TemporaryDirectory() as td:
        packager.package(built_packages, pathlib.Path(td), built_statements)

    console.console.print(
        f'[success]Contest packaged for [item]{packager.name()}[/item]![/success]'
    )


@app.command('polygon', help='Build a contest package for Polygon.')
def polygon(
    verification: environment.VerificationParam,
):
    run_contest_packager(
        PolygonContestPackager, PolygonPackager, verification=verification
    )
