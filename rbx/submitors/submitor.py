import abc
import pathlib
from typing import Any

from rbx.schema import Problem


class Submitor(abc.ABC):
    @abc.abstractmethod
    def key(self) -> str:
        pass

    @abc.abstractmethod
    def should_handle(self, problem: Problem) -> bool:
        pass

    @abc.abstractmethod
    def submit(
        self,
        file: pathlib.Path,
        problem: Problem,
        submitor_config: Any,
        credentials: Any,
    ) -> bool:
        pass
