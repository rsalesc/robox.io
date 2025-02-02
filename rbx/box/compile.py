import pathlib

import typer

from rbx import annotations, console
from rbx.box import code, package
from rbx.box.schema import CodeItem

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


def _compile_out():
    return package.get_build_path() / 'exe'


def _compile(item: CodeItem):
    console.console.print(f'Compiling [item]{item.path}[/item]...')
    digest = code.compile_item(item)
    cacher = package.get_file_cacher()
    out_path = _compile_out()
    cacher.get_file_to_path(digest, out_path)
    out_path.chmod(0o755)

    console.console.print(
        f'[success]Compiled file written at [item]{out_path}[/item].[/success]'
    )


@app.command('any, a', help='Compile an asset given its path.')
@package.within_problem
def any(path: str):
    _compile(CodeItem(path=pathlib.Path(path)))


@app.command('solution, s', help='Compile a solution given its path.')
@package.within_problem
def solution(path: str):
    _compile(package.get_solution(path))


@app.command('generator, gen, g', help='Compile a generator given its name.')
@package.within_problem
def generator(name: str):
    _compile(package.get_generator(name))


@app.command('checker, c', help='Compile the checker.')
@package.within_problem
def checker():
    _compile(package.get_checker())


@app.command('validator, v', help='Compile the main validator.')
@package.within_problem
def validator():
    _compile(package.get_validator())
