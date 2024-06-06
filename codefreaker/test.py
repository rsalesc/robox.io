from typing import Optional
from typing_extensions import Annotated
import typer
import pathlib

from . import hydration
from . import metadata
from .console import console, multiline_prompt
from .schema import Testcase

app = typer.Typer()


@app.command()
def hydrate(problem: Optional[str] = None):
    hydration.main(problem=problem)


@app.command()
def add(problem: str):
    dumped_problem = metadata.find_problem_by_anything(problem)
    if dumped_problem is None:
        console.print(f"[error]Problem [item]{problem}[/item] not found.[/error]")
        return

    input = multiline_prompt("Testcase input")
    output = multiline_prompt("Testcase output")

    hydration.add_testcase(
        pathlib.Path(), dumped_problem, Testcase(input=input, output=output)
    )


@app.command()
def remove(problem: str, i: Annotated[int, typer.Option("--index", "-i")]):
    dumped_problem = metadata.find_problem_by_anything(problem)
    if dumped_problem is None:
        console.print(f"[error]Problem [item]{problem}[/item] not found.[/error]")
        return

    hydration.remove_testcase(pathlib.Path(), dumped_problem, i)
