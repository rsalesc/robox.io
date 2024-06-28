import pathlib
import shutil
from typing import Optional

import typer

from robox import annotations, console
from robox.box import package
from robox.box.schema import CodeItem
from robox.config import get_jngen, get_testlib
from robox.grading import steps

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


def get_local_artifact(name: str) -> Optional[steps.GradingFileInput]:
    path = pathlib.Path(name)
    if path.is_file():
        return steps.GradingFileInput(src=path, dest=path)
    return None


def maybe_add_testlib(code: CodeItem, artifacts: steps.GradingArtifacts):
    # Try to get from compilation files, then from package folder, then from tool.
    artifact = get_local_artifact('testlib.h') or steps.testlib_grading_input()
    compilation_files = package.get_compilation_files(code)
    if any(dest == artifact.dest for _, dest in compilation_files):
        return
    artifacts.inputs.append(artifact)


def maybe_add_jngen(code: CodeItem, artifacts: steps.GradingArtifacts):
    # Try to get from compilation files, then from package folder, then from tool.
    artifact = get_local_artifact('jngen.h') or steps.jngen_grading_input()
    compilation_files = package.get_compilation_files(code)
    if any(dest == artifact.dest for _, dest in compilation_files):
        return
    artifacts.inputs.append(artifact)


@app.command('testlib')
def testlib():
    shutil.copyfile(get_testlib(), pathlib.Path('testlib.h'))
    console.console.print('Downloaded [item]testlib.h[/item] into current package.')


@app.command('jngen')
def jngen():
    shutil.copyfile(get_jngen(), pathlib.Path('jngen.h'))
    console.console.print('Downloaded [item]jngen.h[/item] into current package.')