import pathlib
from typing import List

import typer
from codefreaker.box.package import get_build_testgroup_path
from codefreaker.box.schema import TestcaseGroup
from codefreaker import console


def find_testcases(group: TestcaseGroup) -> List[pathlib.Path]:
    testgroup_path = get_build_testgroup_path(group.name)
    if not testgroup_path.is_dir():
        console.console.print(
            f"Testgroup {group.name} is not generated in build folder"
        )
        raise typer.Exit(1)

    return sorted(testgroup_path.glob("*.in"))
