import functools
import pathlib
from typing import List, Optional, Tuple

import typer

from robox import console, utils
from robox.box.environment import get_sandbox_type
from robox.box.schema import (
    CodeItem,
    ExpectedOutcome,
    Generator,
    Package,
    Solution,
    Stress,
    TestcaseGroup,
)
from robox.config import get_builtin_checker
from robox.grading.caching import DependencyCache
from robox.grading.judge.cacher import FileCacher
from robox.grading.judge.sandbox import SandboxBase
from robox.grading.judge.storage import FilesystemStorage, Storage

YAML_NAME = 'problem.rbx.yml'
_DEFAULT_CHECKER = 'wcmp.cpp'
TEMP_DIR = None


@functools.cache
def find_problem_yaml(root: pathlib.Path = pathlib.Path()) -> Optional[pathlib.Path]:
    problem_yaml_path = root / YAML_NAME
    while root != pathlib.PosixPath('.') and not problem_yaml_path.is_file():
        root = root.parent
        problem_yaml_path = root / YAML_NAME
    if not problem_yaml_path.is_file():
        return None
    return problem_yaml_path


@functools.cache
def find_problem_package(root: pathlib.Path = pathlib.Path()) -> Optional[Package]:
    problem_yaml_path = find_problem_yaml(root)
    if not problem_yaml_path:
        return None
    return utils.model_from_yaml(Package, problem_yaml_path.read_text())


def find_problem_package_or_die(root: pathlib.Path = pathlib.Path()) -> Package:
    package = find_problem_package(root)
    if package is None:
        console.console.print(f'[error]Problem not found in {root.absolute()}[/error]')
        raise typer.Exit(1)
    return package


def find_problem(root: pathlib.Path = pathlib.Path()) -> pathlib.Path:
    found = find_problem_yaml(root)
    if found is None:
        console.console.print(f'[error]Problem not found in {root.absolute()}[/error]')
        raise typer.Exit(1)
    return found.parent


def save_package(
    package: Optional[Package] = None, root: pathlib.Path = pathlib.Path()
) -> None:
    package = package or find_problem_package_or_die(root)
    problem_yaml_path = find_problem_yaml(root)
    if not problem_yaml_path:
        console.console.print(f'[error]Problem not found in {root.absolute()}[/error]')
        raise typer.Exit(1)
    problem_yaml_path.write_text(utils.model_to_yaml(package))


@functools.cache
def get_problem_cache_dir(root: pathlib.Path = pathlib.Path()) -> pathlib.Path:
    cache_dir = find_problem(root) / '.box'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@functools.cache
def get_problem_storage_dir(root: pathlib.Path = pathlib.Path()) -> pathlib.Path:
    storage_dir = get_problem_cache_dir(root) / '.storage'
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def get_problem_runs_dir(root: pathlib.Path = pathlib.Path()) -> pathlib.Path:
    runs_dir = get_problem_cache_dir(root) / 'runs'
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir


@functools.cache
def get_cache_storage(root: pathlib.Path = pathlib.Path()) -> Storage:
    return FilesystemStorage(get_problem_storage_dir(root))


@functools.cache
def get_dependency_cache(root: pathlib.Path = pathlib.Path()) -> DependencyCache:
    return DependencyCache(get_problem_cache_dir(root), get_cache_storage(root))


@functools.cache
def get_file_cacher(root: pathlib.Path = pathlib.Path()) -> FileCacher:
    return FileCacher(get_cache_storage(root))


@functools.cache
def get_digest_as_string(
    digest: str, root: pathlib.Path = pathlib.Path()
) -> Optional[str]:
    cacher = get_file_cacher(root)
    try:
        content = cacher.get_file_content(digest)
        return content.decode()
    except KeyError:
        return None


def get_new_sandbox(root: pathlib.Path = pathlib.Path()) -> SandboxBase:
    return get_sandbox_type()(file_cacher=get_file_cacher(root), temp_dir=TEMP_DIR)


@functools.cache
def get_singleton_sandbox(root: pathlib.Path = pathlib.Path()) -> SandboxBase:
    return get_new_sandbox(root)


@functools.cache
def get_build_path(root: pathlib.Path = pathlib.Path()) -> pathlib.Path:
    return find_problem(root) / 'build'


@functools.cache
def get_build_tests_path(root: pathlib.Path = pathlib.Path()) -> pathlib.Path:
    return get_build_path(root) / 'tests'


@functools.cache
def get_build_testgroup_path(
    group: str, root: pathlib.Path = pathlib.Path()
) -> pathlib.Path:
    res = get_build_tests_path(root) / group
    res.mkdir(exist_ok=True, parents=True)
    return res


@functools.cache
def get_generator(name: str, root: pathlib.Path = pathlib.Path()) -> Generator:
    package = find_problem_package_or_die(root)
    for generator in package.generators:
        if generator.name == name:
            return generator
    console.console.print(f'[error]Generator [item]{name}[/item] not found[/error]')
    raise typer.Exit(1)


@functools.cache
def get_checker(root: pathlib.Path = pathlib.Path()) -> CodeItem:
    package = find_problem_package_or_die(root)

    return package.checker or CodeItem(
        path=get_builtin_checker(_DEFAULT_CHECKER).absolute()
    )


@functools.cache
def get_solutions(root: pathlib.Path = pathlib.Path()) -> List[Solution]:
    package = find_problem_package_or_die(root)
    return package.solutions


@functools.cache
def get_main_solution(root: pathlib.Path = pathlib.Path()) -> Optional[Solution]:
    for solution in get_solutions(root):
        if solution.outcome == ExpectedOutcome.ACCEPTED:
            return solution
    return None


@functools.cache
def get_solution(name: str, root: pathlib.Path = pathlib.Path()) -> Solution:
    for solution in get_solutions(root):
        if str(solution.path) == name:
            return solution
    console.console.print(f'[error]Solution [item]{name}[/item] not found[/error]')
    raise typer.Exit(1)


@functools.cache
def get_stress(name: str, root: pathlib.Path = pathlib.Path()) -> Stress:
    pkg = find_problem_package_or_die(root)
    for stress in pkg.stresses:
        if stress.name == name:
            return stress
    console.console.print(f'[error]Stress [item]{name}[/item] not found[/error]')
    raise typer.Exit(1)


@functools.cache
def get_testgroup(name: str, root: pathlib.Path = pathlib.Path()) -> TestcaseGroup:
    pkg = find_problem_package_or_die(root)
    for testgroup in pkg.testcases:
        if testgroup.name == name:
            return testgroup
    console.console.print(f'[error]Test group [item]{name}[/item] not found[/error]')
    raise typer.Exit(1)


# Return each compilation file and to where it should be moved inside
# the sandbox.
def get_compilation_files(code: CodeItem) -> List[Tuple[pathlib.Path, pathlib.Path]]:
    code_dir = code.path.parent.resolve()

    res = []
    for compilation_file in code.compilationFiles or []:
        compilation_file_path = pathlib.Path(compilation_file).resolve()
        if not compilation_file_path.is_file():
            console.console.print(
                f'[error]Compilation file [item]{compilation_file}[/item] for '
                f'code [item]{code.path}[/item] does not exist.[/error]',
            )
            raise typer.Exit(1)
        if not compilation_file_path.is_relative_to(code_dir):
            console.console.print(
                f'[error]Compilation file [item]{compilation_file}[/item] for '
                f"code [item]{code.path}[/item] is not under the code's folder.[/error]",
            )
            raise typer.Exit(1)

        res.append(
            (
                pathlib.Path(compilation_file),
                compilation_file_path.relative_to(code_dir),
            )
        )
    return res
