import itertools
from typing import List
from pydantic import BaseModel

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

  def get_file_basename(self):
    name = name.replace(' ', '_')
    name = name.replace('.', '_')
    name = name.strip('_')
    return ''.join(i for i, _ in itertools.groupby(name))