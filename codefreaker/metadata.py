import pathlib
from typing import List, Optional

from .schema import DumpedProblem


def find_problem_by_code(code: str, root: Optional[pathlib.Path] = None) -> Optional[DumpedProblem]:
  if not root:
    root = pathlib.Path()
  
  metadata_path = root / f'{code}.cfk.json'
  if not metadata_path.is_file():
    return None
  return DumpedProblem.model_validate_json(metadata_path.read_text())

def find_problems(root: Optional[pathlib.Path] = None) -> List[DumpedProblem]:
  if not root:
    root = pathlib.Path()
  
  problems = []
  for metadata_path in root.glob('*.cfk.json'):
    problems.append(DumpedProblem.model_validate_json(metadata_path.read_text()))
  return problems