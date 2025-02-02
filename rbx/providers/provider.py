import abc
from typing import List

from rbx.schema import Problem


class ProviderInterface(abc.ABC):
    @abc.abstractmethod
    def should_handle(self, url: str) -> bool:
        pass

    def is_contest(self, problems: List[Problem]) -> bool:
        batches = set(problem.batch.id for problem in problems)
        return len(batches) == 1

    def should_simplify_contest_problems(self) -> bool:
        return False

    def get_problem_code_within_contest(self, problem: Problem) -> str:
        return self.get_code(problem)

    def get_code(self, problem: Problem) -> str:
        return problem.name

    def get_aliases(self, problem: Problem) -> List[str]:
        return []
