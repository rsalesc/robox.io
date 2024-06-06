import abc
from typing import List, Set

from codefreaker.schema import Problem

class ProviderInterface(abc.ABC):
  @abc.abstractmethod
  def should_handle(self, url: str) -> bool:
    pass
  
  @abc.abstractmethod
  def get_code(self, problem: Problem) -> str:
    return problem.name
  
  @abc.abstractmethod
  def get_aliases(self, problem: Problem) -> List[str]:
    return []