from typing import List

from rbx.providers.codeforces import CodeforcesProvider
from rbx.providers.provider import ProviderInterface
from rbx.schema import Problem

ALL_PROVIDERS: List[ProviderInterface] = [
    CodeforcesProvider(),
]


def is_contest(problems: List[Problem]) -> bool:
    for provider in ALL_PROVIDERS:
        handle_all = all(provider.should_handle(problem.url) for problem in problems)
        if handle_all:
            return provider.is_contest(problems)
    return False


def should_simplify_contest_problems(problems: List[Problem]) -> bool:
    if not is_contest(problems):
        return False
    for provider in ALL_PROVIDERS:
        handle_all = all(provider.should_handle(problem.url) for problem in problems)
        if handle_all:
            return provider.should_simplify_contest_problems()
    return False


def get_code(problem: Problem, simplify: bool = False) -> str:
    for provider in ALL_PROVIDERS:
        if provider.should_handle(problem.url):
            if simplify:
                return provider.get_problem_code_within_contest(problem)
            return provider.get_code(problem)
    return problem.get_normalized_name()


def get_aliases(problem: Problem) -> List[str]:
    for provider in ALL_PROVIDERS:
        if provider.should_handle(problem.url):
            return provider.get_aliases(problem)
    return []
