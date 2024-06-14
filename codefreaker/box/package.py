import pathlib
from typing import Optional

from codefreaker import utils
from codefreaker.box.schema import Package

YAML_NAME = "problem.cfk.yaml"


def find_problem_yaml(root: pathlib.Path = pathlib.Path(".")) -> Optional[pathlib.Path]:
    problem_yaml_path = root / YAML_NAME
    while root != pathlib.PosixPath(".") and not problem_yaml_path.is_file():
        root = root.parent
        problem_yaml_path = root / YAML_NAME
    if not problem_yaml_path.is_file():
        return None
    return problem_yaml_path


def find_problem_package(root: pathlib.Path = pathlib.Path(".")) -> Optional[Package]:
    problem_yaml_path = find_problem_yaml(root)
    if not problem_yaml_path:
        return None
    return utils.model_from_yaml(Package, problem_yaml_path.read_text())


def find_problem(root: pathlib.Path = pathlib.Path(".")) -> Optional[Package]:
    found = find_problem_yaml(root)
    if found is None:
        return None
    return found.parent
