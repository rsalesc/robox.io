import itertools
from typing import Dict, List
from pydantic import BaseModel

from . import utils

class Testcase(BaseModel):
  input: str
  output: str

class Batch(BaseModel):
  id: str
  size: int

class Problem(BaseModel):
  name: str
  group: str
  url: str
  interactive: bool
  memoryLimit: int
  timeLimit: int
  tests: List[Testcase]
  testType: str
  batch: Batch

  def get_file_basename(self) -> str:
    return utils.normalize_with_underscores(self.name)
  
  def get_vars(self) -> Dict[str, str]:
    return {
      'problem_name': self.name,
      'problem_code': self.get_file_basename(),
      'problem_url': self.url,
      'problem_contest': self.group,
      'problem_time_limit': f'{self.timeLimit}ms',
      'problem_memory_limit': f'{self.memoryLimit}MB',
      'problem_test_type': self.testType,
    }