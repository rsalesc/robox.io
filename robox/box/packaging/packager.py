import pathlib
from abc import ABC, abstractmethod
from typing import List, Tuple

from robox.box import package
from robox.box.generators import get_all_built_testcases
from robox.box.schema import Testcase, TestcaseGroup
from robox.box.statements.schema import Statement


class BasePackager(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    def languages(self):
        # TODO
        return ['en']

    def get_built_testcases_per_group(self):
        return get_all_built_testcases()

    def get_built_testcases(self) -> List[Tuple[TestcaseGroup, List[Testcase]]]:
        pkg = package.find_problem_package_or_die()
        tests_per_group = self.get_built_testcases_per_group()
        return [(group, tests_per_group[group.name]) for group in pkg.testcases]

    def get_flattened_built_testcases(self) -> List[Testcase]:
        pkg = package.find_problem_package_or_die()
        tests_per_group = self.get_built_testcases_per_group()

        res = []
        for group in pkg.testcases:
            res.extend(tests_per_group[group.name])
        return res

    def get_statement_for_language(self, lang: str) -> Statement:
        pkg = package.find_problem_package_or_die()
        for statement in pkg.statements:
            if statement.language == lang:
                return statement
        raise

    @abstractmethod
    def package(self, build_path: pathlib.Path, into_path: pathlib.Path):
        pass
