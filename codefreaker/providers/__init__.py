from typing import List

from codefreaker.schema import Problem

from .codeforces import CodeforcesProvider
from .provider import ProviderInterface


ALL_PROVIDERS: List[ProviderInterface] = [
  CodeforcesProvider(),
]

def get_code(problem: Problem) -> str:
  for provider in ALL_PROVIDERS:
    if provider.should_handle(problem.url):
      return provider.get_code(problem)
  return problem.get_normalized_name()

def get_aliases(problem: Problem) -> List[str]:
  for provider in ALL_PROVIDERS:
    if provider.should_handle(problem.url):
      return provider.get_aliases(problem)
  return []