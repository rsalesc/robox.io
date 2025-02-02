import pathlib
from typing import List, Optional, Tuple

from rbx import config, hydration, metadata
from rbx.console import console
from rbx.schema import DumpedProblem, Testcase
from rbx.test import get_testcases_io


def get_testcase_paths(
    root: pathlib.Path, problem: DumpedProblem, i: int
) -> Tuple[pathlib.Path, pathlib.Path]:
    return (root / f'{problem.code}.{i}.in', root / f'{problem.code}.{i}.out')


def hydrate_problem(root: pathlib.Path, problem: DumpedProblem):
    for i, testcase in enumerate(problem.tests or []):
        in_path, out_path = get_testcase_paths(root, problem, i)
        in_path.write_text(testcase.input)
        out_path.write_text(testcase.output)


def add_testcase(root: pathlib.Path, problem: DumpedProblem, testcase: Testcase):
    problem_path = metadata.find_problem_path_by_code(problem.code, root)
    if not problem_path or not problem_path.is_file():
        console.print(
            f'[error]Problem [item]{problem.pretty_name()}[/item] not found.[/error]'
        )
        return

    # Pick next number.
    i = max([tc.index for tc in get_testcases_io(problem, root)] + [-1]) + 1
    in_path, out_path = get_testcase_paths(root, problem, i)
    in_path.write_text(testcase.input)
    out_path.write_text(testcase.output)

    console.print(
        f'Added testcase [item]{i}[/item] to problem [item]{problem.pretty_name()}[/item].'
    )


def remove_testcase(root: pathlib.Path, problem: DumpedProblem, i: int):
    problem_path = metadata.find_problem_path_by_code(problem.code, root)
    if not problem_path or not problem_path.is_file():
        console.print(
            f'[error]Problem [item]{problem.pretty_name()}[/item] not found.[/error]'
        )
        return

    testcases = get_testcases_io(problem, root)
    testcases = [testcase for testcase in testcases if testcase.index == i]
    if not testcases:
        console.print(
            f'[error]Testcase [item]{i}[/item] not found in problem [item]{problem.pretty_name()}[/item].[/error]'
        )
        return
    if testcases[0].input:
        testcases[0].input.unlink(missing_ok=True)
    if testcases[0].output:
        testcases[0].output.unlink(missing_ok=True)

    console.print(
        f'Removed testcase [item]{i}[/item] from problem [item]{problem.pretty_name()}[/item].'
    )


def edit_testcase(root: pathlib.Path, problem: DumpedProblem, i: int):
    problem_path = metadata.find_problem_path_by_code(problem.code, root)
    if not problem_path or not problem_path.is_file():
        console.print(
            f'[error]Problem [item]{problem.pretty_name()}[/item] not found.[/error]'
        )
        return

    testcases = get_testcases_io(problem, root)
    testcases = [testcase for testcase in testcases if testcase.index == i]
    if not testcases:
        console.print(
            f'[error]Testcase [item]{i}[/item] not found in problem [item]{problem.pretty_name()}[/item].[/error]'
        )
        return

    paths: List[Optional[pathlib.Path]] = [testcases[0].input, testcases[0].output]
    config.open_editor(*[path for path in paths if path is not None and path.is_file()])


def main(problem: Optional[str] = None):
    problems_to_hydrate = []
    if not problem:
        problems_to_hydrate = metadata.find_problems()
    else:
        dumped_problem = metadata.find_problem_by_anything(problem)
        problems_to_hydrate.append(dumped_problem)

    root = pathlib.Path()

    for dumped_problem in problems_to_hydrate:
        console.print(
            f'Hydrating problem [item]{dumped_problem.pretty_name()}[/item]...'
        )
        hydration.hydrate_problem(root, dumped_problem)
