import itertools
from typing import Dict, List, Optional
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

  def get_code(self):
    return self.get_normalized_name()

  def get_normalized_name(self) -> str:
    return utils.normalize_with_underscores(self.name)
  
class DumpedProblem(Problem):
  code: str
  aliases: List[str]

  def get_vars(self) -> Dict[str, str]:
    return {
      'problem_name': self.name,
      'problem_code': self.code,
      'problem_url': self.url,
      'problem_contest': self.group,
      'problem_time_limit': f'{self.timeLimit}ms',
      'problem_memory_limit': f'{self.memoryLimit}MB',
      'problem_test_type': self.testType,
    }