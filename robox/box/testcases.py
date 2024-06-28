import pathlib
from typing import List

import typer
from pydantic import BaseModel

from robox import console
from robox.box import package
from robox.box.package import get_build_testgroup_path
from robox.box.schema import Testcase, TestcaseGroup


class TestcaseData(BaseModel):
    input: str
    output: str


def find_built_testcases(group: TestcaseGroup) -> List[Testcase]:
    inputs = find_built_testcase_inputs(group)

    testcases = []
    for input in inputs:
        output = input.with_suffix('.out')
        testcases.append(Testcase(inputPath=input, outputPath=output))
    return testcases


def find_built_testcase_inputs(group: TestcaseGroup) -> List[pathlib.Path]:
    testgroup_path = get_build_testgroup_path(group.name)
    if not testgroup_path.is_dir():
        console.console.print(
            f'Testgroup {group.name} is not generated in build folder'
        )
        raise typer.Exit(1)

    return sorted(testgroup_path.glob('*.in'))


def get_samples() -> List[Testcase]:
    tcs = find_built_testcases(package.get_testgroup('samples'))
    return [
        Testcase(
            inputPath=tc.inputPath.resolve(),
            outputPath=tc.outputPath.resolve()
            if tc.outputPath is not None and tc.outputPath.is_file()
            else None,
        )
        for tc in tcs
    ]
