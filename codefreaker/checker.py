from pathlib import PosixPath
import pathlib
from typing import Optional
from typing_extensions import Annotated
import typer

from codefreaker import metadata, utils
from codefreaker.config import get_builtin_checker
from codefreaker.console import console


app = typer.Typer(no_args_is_help=True)


@app.command()
def add(
    problem: str,
    template: Annotated[
        Optional[str],
        typer.Option(
            "--template", "-t", help="Checker that should be used as template."
        ),
    ] = None,
):
    """
    Add a new checker for the problem.
    """
    dumped_problem = metadata.find_problem_by_anything(problem)
    if dumped_problem is None:
        console.print(f"[error]Problem [item]{problem}[/item] not found.[/error]")
        return

    template_path = get_builtin_checker(template or "boilerplate.cpp")

    if not template_path.is_file():
        console.print(f"[error]Template file {template} not found.[/error]")
        return

    testlib_path = get_builtin_checker("testlib.h")
    if not testlib_path.is_file():
        console.print("[error]Testlib file not found.[/error]")
        return

    checker_name = f"{dumped_problem.code}.checker.cpp"
    checker_path = pathlib.Path() / checker_name

    # Create both files.
    checker_path.write_text(template_path.read_text())
    (checker_path.parent / "testlib.h").write_text(testlib_path.read_text())

    # Set checker.
    problem_to_dump = dumped_problem.model_copy()
    problem_to_dump.checker = checker_name
    metadata.find_problem_path_by_code(dumped_problem.code).write_text(
        utils.model_json(problem_to_dump)
    )
    console.print(
        f"Checker [item]{checker_name}[/item] added to problem [item]{dumped_problem.pretty_name()}[/item]."
    )


@app.command()
def set(problem: str, checker: str):
    """
    Set a checker for the problem.
    """
    dumped_problem = metadata.find_problem_by_anything(problem)
    if dumped_problem is None:
        console.print(f"[error]Problem [item]{problem}[/item] not found.[/error]")
        return

    problem_to_dump = dumped_problem.model_copy()
    problem_to_dump.checker = checker
    metadata.find_problem_path_by_code(dumped_problem.code).write_text(
        utils.model_json(problem_to_dump)
    )
    console.print(
        f"Checker [item]{checker}[/item] will be used for problem [item]{dumped_problem.pretty_name()}[/item]."
    )


@app.command()
def unset(problem: str):
    """
    Use the default checker for a problem.
    """
    dumped_problem = metadata.find_problem_by_anything(problem)
    if dumped_problem is None:
        console.print(f"[error]Problem [item]{problem}[/item] not found.[/error]")
        return

    problem_to_dump = dumped_problem.model_copy()
    problem_to_dump.checker = None
    metadata.find_problem_path_by_code(dumped_problem.code).write_text(
        utils.model_json(problem_to_dump)
    )
    console.print(
        f"Default checker will be used for problem [item]{dumped_problem.pretty_name()}[/item]."
    )
