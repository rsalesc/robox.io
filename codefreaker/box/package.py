import functools
import pathlib
from typing import Optional

import typer

from codefreaker import console, utils
from codefreaker.box.environment import get_sandbox_type
from codefreaker.box.schema import Generator, Package
from codefreaker.grading.caching import DependencyCache
from codefreaker.grading.judge.cacher import FileCacher
from codefreaker.grading.judge.sandbox import SandboxBase
from codefreaker.grading.judge.storage import FilesystemStorage, Storage

YAML_NAME = "problem.cfk.yml"
TEMP_DIR = None


@functools.cache
def find_problem_yaml(root: pathlib.Path = pathlib.Path(".")) -> Optional[pathlib.Path]:
    problem_yaml_path = root / YAML_NAME
    while root != pathlib.PosixPath(".") and not problem_yaml_path.is_file():
        root = root.parent
        problem_yaml_path = root / YAML_NAME
    if not problem_yaml_path.is_file():
        return None
    return problem_yaml_path


@functools.cache
def find_problem_package(root: pathlib.Path = pathlib.Path(".")) -> Optional[Package]:
    problem_yaml_path = find_problem_yaml(root)
    if not problem_yaml_path:
        return None
    return utils.model_from_yaml(Package, problem_yaml_path.read_text())


def find_problem_package_or_die(root: pathlib.Path = pathlib.Path(".")) -> Package:
    package = find_problem_package(root)
    if package is None:
        console.console.print(f"Problem not found in {root.absolute()}", style="error")
        raise typer.Exit(1)
    return package


def find_problem(root: pathlib.Path = pathlib.Path(".")) -> pathlib.Path:
    found = find_problem_yaml(root)
    if found is None:
        return None
    return found.parent


@functools.cache
def get_problem_cache_dir(root: pathlib.Path = pathlib.Path(".")) -> pathlib.Path:
    cache_dir = find_problem(root) / ".box"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@functools.cache
def get_problem_storage_dir(root: pathlib.Path = pathlib.Path(".")) -> pathlib.Path:
    storage_dir = get_problem_cache_dir(root) / ".storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@functools.cache
def get_cache_storage(root: pathlib.Path = pathlib.Path(".")) -> Storage:
    return FilesystemStorage(get_problem_storage_dir(root))


@functools.cache
def get_dependency_cache(root: pathlib.Path = pathlib.Path(".")) -> DependencyCache:
    return DependencyCache(get_problem_cache_dir(root), get_cache_storage(root))


@functools.cache
def get_file_cacher(root: pathlib.Path = pathlib.Path(".")) -> FileCacher:
    return FileCacher(get_cache_storage(root))


def get_new_sandbox(root: pathlib.Path = pathlib.Path(".")) -> SandboxBase:
    return get_sandbox_type()(file_cacher=get_file_cacher(root), temp_dir=TEMP_DIR)


@functools.cache
def get_singleton_sandbox(root: pathlib.Path = pathlib.Path(".")) -> SandboxBase:
    return get_new_sandbox(root)


@functools.cache
def get_build_path(root: pathlib.Path = pathlib.Path(".")) -> pathlib.Path:
    return find_problem(root) / "build"


@functools.cache
def get_build_tests_path(root: pathlib.Path = pathlib.Path(".")) -> pathlib.Path:
    return get_build_path(root) / "tests"


@functools.cache
def get_build_testgroup_path(
    group: str, root: pathlib.Path = pathlib.Path(".")
) -> pathlib.Path:
    res = get_build_tests_path(root) / group
    res.mkdir(exist_ok=True, parents=True)
    return res


@functools.cache
def get_generator(name: str, root: pathlib.Path = pathlib.Path(".")) -> Generator:
    package = find_problem_package(root)
    for generator in package.generators:
        if generator.name == name:
            return generator
    console.console.print(f"Generator {name} not found", style="error")
    raise typer.Exit(1)
