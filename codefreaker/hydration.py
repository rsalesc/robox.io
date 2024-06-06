import pathlib
from typing import Optional

from . import metadata
from . import hydration
from .schema import DumpedProblem, Problem
from .console import console

def get_testcase_paths(root: pathlib.Path, problem: DumpedProblem, i: int) -> pathlib.Path:
  return (root / f'{problem.code}.{i}.in', root / f'{problem.code}.{i}.out')

def hydrate_problem(root: pathlib.Path, problem: DumpedProblem):
  for i, testcase in enumerate(problem.tests):
    in_path, out_path = get_testcase_paths(root, problem, i)
    in_path.write_text(testcase.input)
    out_path.write_text(testcase.output)

def main(problem: Optional[str] = None):
  problems_to_hydrate = []
  if not problem:
    problems_to_hydrate = metadata.find_problems()
  else:
    dumped_problem = metadata.find_problem_by_code(problem)
    problems_to_hydrate.append(dumped_problem)

  root = pathlib.Path()
  
  for dumped_problem in problems_to_hydrate:
    console.print(f'Hydrating problem [item]{dumped_problem.code}[/item]...')
    hydration.hydrate_problem(root, dumped_problem)