import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel

from rbx import utils


class Testcase(BaseModel):
    input: str
    output: str


class Batch(BaseModel):
    id: str
    size: int

    @staticmethod
    def create():
        return Batch(id=str(uuid.uuid4()), size=1)


class Problem(BaseModel):
    name: str
    group: str = ''
    url: str = ''
    interactive: bool = False
    memoryLimit: int
    timeLimit: int
    tests: List[Testcase] = []
    testType: str = 'single'
    batch: Batch

    def get_code(self):
        return self.get_normalized_name()

    def get_normalized_name(self) -> str:
        return utils.normalize_with_underscores(self.name)


class DumpedProblem(Problem):
    code: str
    aliases: List[str]
    checker: Optional[str] = None

    @staticmethod
    def from_problem(problem: Problem, **kwargs) -> 'DumpedProblem':
        return DumpedProblem(**problem.model_dump(), **kwargs)

    def pretty_name(self) -> str:
        if self.name == self.code:
            return self.name
        return f'{self.name} ({self.code})'

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
