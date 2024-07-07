import functools
import pathlib
from typing import List, Optional

import typer

from robox import console, utils
from robox.box.contest.schema import Contest
from robox.box.package import find_problem_package_or_die
from robox.box.schema import Package

YAML_NAME = 'contest.rbx.yml'


@functools.cache
def find_contest_yaml(root: pathlib.Path = pathlib.Path()) -> Optional[pathlib.Path]:
    contest_yaml_path = root / YAML_NAME
    while root != pathlib.PosixPath('.') and not contest_yaml_path.is_file():
        root = root.parent
        contest_yaml_path = root / YAML_NAME
    if not contest_yaml_path.is_file():
        return None
    return contest_yaml_path


@functools.cache
def find_contest_package(root: pathlib.Path = pathlib.Path()) -> Optional[Contest]:
    contest_yaml_path = find_contest_yaml(root)
    if not contest_yaml_path:
        return None
    return utils.model_from_yaml(Contest, contest_yaml_path.read_text())


def find_contest_package_or_die(root: pathlib.Path = pathlib.Path()) -> Contest:
    package = find_contest_package(root)
    if package is None:
        console.console.print(f'Contest not found in {root.absolute()}', style='error')
        raise typer.Exit(1)
    return package


def find_contest(root: pathlib.Path = pathlib.Path()) -> pathlib.Path:
    found = find_contest_yaml(root)
    if found is None:
        console.console.print(f'Contest not found in {root.absolute()}', style='error')
        raise typer.Exit(1)
    return found.parent


def save_contest(
    package: Optional[Contest] = None, root: pathlib.Path = pathlib.Path()
) -> None:
    package = package or find_contest_package_or_die(root)
    contest_yaml_path = find_contest_yaml(root)
    if not contest_yaml_path:
        console.console.print(f'Contest not found in {root.absolute()}', style='error')
        raise typer.Exit(1)
    contest_yaml_path.write_text(utils.model_to_yaml(package))


def get_problems(contest: Contest) -> List[Package]:
    problems = []
    for problem in contest.problems:
        problems.append(find_problem_package_or_die(problem.get_path()))
    return problems
