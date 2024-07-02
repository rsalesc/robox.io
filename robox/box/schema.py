from __future__ import annotations

import pathlib
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from robox.autoenum import AutoEnum, alias
from robox.box.statements.schema import Statement
from robox.grading.steps import Outcome

Primitive = str | int | float | bool


def NameField(**kwargs):
    return Field(pattern=r'^[a-zA-Z0-9\-]+$', min_length=3, **kwargs)


class ExpectedOutcome(AutoEnum):
    ACCEPTED = alias('accepted', 'ac', 'correct')  # type: ignore
    WRONG_ANSWER = alias('wrong answer', 'wa')  # type: ignore
    INCORRECT = alias('fail', 'incorrect')  # type: ignore
    RUNTIME_ERROR = alias('runtime error', 'rte', 're')  # type: ignore
    TIME_LIMIT_EXCEEDED = alias('time limit exceeded', 'timeout', 'tle')  # type: ignore
    MEMORY_LIMIT_EXCEEDED = alias('memory limit exceeded', 'mle')  # type: ignore
    TLE_OR_RTE = alias('tle or rte', 'tle/rte', 'tle+rte')  # type: ignore

    def match(self, outcome: Outcome) -> bool:
        match self:
            case ExpectedOutcome.ACCEPTED:
                return outcome == Outcome.ACCEPTED
            case ExpectedOutcome.WRONG_ANSWER:
                return outcome == Outcome.WRONG_ANSWER
            case ExpectedOutcome.INCORRECT:
                return outcome in {
                    Outcome.WRONG_ANSWER,
                    Outcome.RUNTIME_ERROR,
                    Outcome.MEMORY_LIMIT_EXCEEDED,
                    Outcome.TIME_LIMIT_EXCEEDED,
                }
            case ExpectedOutcome.RUNTIME_ERROR:
                return outcome == Outcome.RUNTIME_ERROR
            case ExpectedOutcome.TIME_LIMIT_EXCEEDED:
                return outcome == Outcome.TIME_LIMIT_EXCEEDED
            case ExpectedOutcome.MEMORY_LIMIT_EXCEEDED:
                return outcome == Outcome.MEMORY_LIMIT_EXCEEDED
            case ExpectedOutcome.TLE_OR_RTE:
                return outcome in {Outcome.TIME_LIMIT_EXCEEDED, Outcome.RUNTIME_ERROR}
            case _:
                return False


class CodeItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # The path of a file containing the code, relative to the package directory.
    path: pathlib.Path

    # The language identifier the could should be compiled/run in.
    language: Optional[str] = None

    # Extra files that should be placed alongside the code file during its
    # compilation, such as testlib.h, jngen.h, etc.
    # The paths are relative to the package directory, but will be included relative
    # to the `path` directory.
    #
    # Testlib and jngen are already included by default.
    compilationFiles: Optional[List[str]] = []


class Testcase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # The path of the input file, relative to the package directory.
    inputPath: pathlib.Path

    # The path of the output file, relative to the package directory.
    outputPath: Optional[pathlib.Path] = None


class GeneratorCall(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # The identifier of the generator to call.
    name: str = NameField()

    # The args to pass to this generator.
    # In case of a generator being called from a Stress test,
    # these args can contain patterns such as `[1..10]` or `(abc|def)`.
    args: Optional[str] = None


class TestcaseGroup(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # The name of this test group.
    name: str = NameField()

    # Testcases below will be added to this group in the order
    # they're defined, from `testcases` first to `generatorScript` last.

    # The path to testcases relative to the package directory
    # to add to this group.
    testcases: List[Testcase] = []

    # A Python glob that matches input file paths relative to the
    # package directory. The globbed files should end with the extension
    # ".in", and their corresponding outputs should have the same file name,
    # but ending with ".out".
    testcaseGlob: Optional[str] = None

    # The generators to call to generate testcases for this group.
    generators: List[GeneratorCall] = []

    # A generator script to call to generate testcases for this group.
    generatorScript: Optional[CodeItem] = None

    # A validator to use to validate the testcases of this group.
    # If not specified, will use the package-level validator.
    # Useful in cases where the constraints vary across test groups.
    validator: Optional[CodeItem] = None

    # The weight of this group in the final score. Useful for
    # problems that have points.
    weight: Optional[float] = 1.0


class Generator(CodeItem):
    model_config = ConfigDict(extra='forbid')

    # The name of this generator.
    # This can be further referenced in testcase groups and
    # stress tests.
    name: str = NameField()


class Solution(CodeItem):
    model_config = ConfigDict(extra='forbid')

    # The expected outcome of this solution.
    outcome: ExpectedOutcome


class Stress(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # The name of this stress test.
    name: str = NameField()

    # Generator pattern to call during stress-test.
    # E.g. "gen1 10 [5..10] abacaba"
    generator: GeneratorCall

    # Path of the solutions to be stress-tested.
    # If empty, will stress-test only the main solution for
    # non-WA verdicts.
    solutions: List[str] = []

    # What verdict to look for while stress-testing.
    outcome: ExpectedOutcome = ExpectedOutcome.INCORRECT


class Package(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Name of the problem.
    name: str = NameField()

    # Time limit of the problem, in milliseconds.
    timeLimit: int

    # Memory limit of the problem, in MB.
    memoryLimit: int

    # Definition of the checker for this problem.
    checker: Optional[CodeItem] = None

    # Definition of the validator for this problem.
    validator: Optional[CodeItem] = None

    # Definitions of the generators for this problem.
    generators: List[Generator] = []

    # All tested solutions for this problem.
    # The first solution in this list is the default solution --
    # the one that will be used as reference -- and should have
    # the `accepted` outcome.
    solutions: List[Solution] = []

    # Test groups for the problem.
    testcases: List[TestcaseGroup] = []

    # List of pre-defined stress tests.
    stresses: List[Stress] = []

    # Statements for the problem.
    statements: List[Statement] = []

    # Vars to be re-used across the package.
    #   - It will be passed as --key=value arguments to the validator.
    #   - It will be available as \VAR{key} variables in the robox statement.
    vars: Dict[str, Primitive] = {}

    @model_validator(mode='after')
    def check_first_solution_is_main(self):
        if self.solutions:
            if self.solutions[0].outcome != ExpectedOutcome.ACCEPTED:
                raise PydanticCustomError(
                    'MISSING_MAIN_SOLUTION',
                    'The first solution in the package must have the "ACCEPTED" outcome.',
                )
        return self

    @model_validator(mode='after')
    def samples_come_first(self):
        for i, group in enumerate(self.testcases):
            if group.name == 'samples' and i > 0:
                raise PydanticCustomError(
                    'SAMPLES_NOT_FIRST',
                    'The "samples" group must be the first group in the package, but is actually the {i}-th',
                    {'i': i + 1},
                )
        return self
