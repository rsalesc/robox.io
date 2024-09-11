import pathlib

import typer

from robox import annotations, console
from robox.box import code, package
from robox.box.schema import CodeItem

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
def any(path: str):
    _compile(CodeItem(path=pathlib.Path(path)))


@app.command('solution, s', help='Compile a solution given its path.')
def solution(path: str):
    _compile(package.get_solution(path))


@app.command('generator, gen, g', help='Compile a generator given its name.')
def generator(name: str):
    _compile(package.get_generator(name))


@app.command('checker, c', help='Compile the checker.')
def checker():
    _compile(package.get_checker())


@app.command('validator, v', help='Compile the main validator.')
def validator():
    _compile(package.get_validator())
