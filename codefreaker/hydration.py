import pathlib
from typing import Optional, Tuple
from filelock import FileLock

from . import metadata
from . import hydration
from .schema import DumpedProblem, Problem, Testcase
from .console import console

def get_testcase_paths(root: pathlib.Path, problem: DumpedProblem, i: int) -> Tuple[pathlib.Path, pathlib.Path]:
  return (root / f'{problem.code}.{i}.in', root / f'{problem.code}.{i}.out')

def hydrate_problem(root: pathlib.Path, problem: DumpedProblem):
  for i, testcase in enumerate(problem.tests):
    in_path, out_path = get_testcase_paths(root, problem, i)
    in_path.write_text(testcase.input)
    out_path.write_text(testcase.output)

def add_testcase(root: pathlib.Path, problem: DumpedProblem, testcase: Testcase):
  problem_path = metadata.find_problem_path_by_code(problem.code, root)
  if not problem_path.is_file():
    console.print(f'[error]Problem [item]{problem.code}[/item] not found.[/error]')
    return

  i = len(problem.tests)
  in_path, out_path = get_testcase_paths(root, problem, i)
  in_path.write_text(testcase.input)
  out_path.write_text(testcase.output)
  problem.tests.append(testcase)
  metadata.find_problem_path_by_code(problem.code, root).write_text(problem.model_dump_json())
  
  console.print(f'Added testcase [item]{i}[/item] to problem [item]{problem.code}[/item].')

def remove_testcase(root: pathlib.Path, problem: DumpedProblem, i: int):
  problem_path = metadata.find_problem_path_by_code(problem.code, root)
  if not problem_path.is_file():
    console.print(f'[error]Problem [item]{problem.code}[/item] not found.[/error]')
    return
  
  if i >= len(problem.tests):
    console.print(f'[error]Testcase [item]{i}[/item] not found in problem [item]{problem.code}[/item] metadata.[/error]')

  in_path, out_path = get_testcase_paths(root, problem, i)
  in_path.unlink(missing_ok=True)
  out_path.unlink(missing_ok=True)
  if i >= len(problem.tests):
    console.print(f'[error]Testcase [item]{i}[/item] not found in problem [item]{problem.code}[/item] metadata.[/error]')
  else:
    problem.tests.pop(i)
    metadata.find_problem_path_by_code(problem.code, root).write_text(problem.model_dump_json())
  
  console.print(f'Removed testcase [item]{i}[/item] from problem [item]{problem.code}[/item].')

def main(problem: Optional[str] = None):
  problems_to_hydrate = []
  if not problem:
    problems_to_hydrate = metadata.find_problems()
  else:
    dumped_problem = metadata.find_problem_by_anything(problem)
    problems_to_hydrate.append(dumped_problem)

  root = pathlib.Path()
  
  for dumped_problem in problems_to_hydrate:
    console.print(f'Hydrating problem [item]{dumped_problem.code}[/item]...')
    hydration.hydrate_problem(root, dumped_problem)