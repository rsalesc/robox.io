import pathlib
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from codefreaker.autoenum import AutoEnum, alias


class ExpectedOutcome(AutoEnum):
    ACCEPTED = alias('accepted', 'ac', 'correct')
    WRONG_ANSWER = alias('wrong answer', 'wa')
    INCORRECT = alias('fail', 'incorrect')
    RUNTIME_ERROR = alias('runtime error', 'rte', 're')
    TIME_LIMIT_EXCEEDED = alias('time limit exceeded', 'timeout', 'tle')
    MEMORY_LIMIT_EXCEEDED = alias('memory limit exceeded', 'mle')
    TLE_OR_RTE = alias('tle or rte', 'tle/rte', 'tle+rte')


class CodeItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # The path of a file containing the code, relative to the package directory.
    path: pathlib.Path

    # The language identifier the could should be compiled/run in.
    language: Optional[str] = None

    # Extra files that should be placed alongside the code file during its
    # compilation, such as testlib.h
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
    name: str

    # The args to pass to this generator.
    args: Optional[str] = None


class TestcaseGroup(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # The name of this test group.
    name: str

    # Testcases below will be added to this group in the order
    # they're defined, from `testcases` first to `generatorScript` last.

    # The path to testcases relative to the package directory
    # to add to this group.
    testcases: Optional[List[Testcase]] = []

    # A Python glob that matches input file paths relative to the
    # package directory. The globbed files should end with the extension
    # ".in", and their corresponding outputs should have the same file name,
    # but ending with ".out".
    testcaseGlob: Optional[str] = None

    # The generators to call to generate testcases for this group.
    generators: Optional[List[GeneratorCall]] = []

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
    name: str


class Solution(CodeItem):
    model_config = ConfigDict(extra='forbid')

    # The expected outcome of this solution.
    outcome: ExpectedOutcome


class Package(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Name of the problem.
    name: str

    # Time limit of the problem, in milliseconds.
    timeLimit: int

    # Memory limit of the problem, in MB.
    memoryLimit: int

    # Definition of the checker for this problem.
    checker: Optional[CodeItem] = None

    # Definition of the validator for this problem.
    validator: Optional[CodeItem] = None

    # Definitions of the generators for this problem.
    generators: Optional[List[Generator]] = None

    # All tested solutions for this problem.
    # The first solution in this list is the default solution --
    # the one that will be used as reference -- and should have
    # the `accepted` outcome.
    solutions: Optional[List[Solution]] = []

    # Test groups for the problem.
    testcases: Optional[List[TestcaseGroup]] = []
