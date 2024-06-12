from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class ExpectedOutcome(Enum):
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong-answer"
    INCORRECT = "incorrect"
    RUNTIME_ERROR = "runtime-error"
    TIME_LIMIT_EXCEEDED = "time-limit-exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory-limit-exceeded"


class CodeItem(BaseModel):
    # The path of a file containing the code, relative to the package directory.
    path: str

    # The language identifier the could should be compiled/run in.
    language: Optional[str] = None

    # Extra files that should be placed alongside the code file during its
    # compilation, such as testlib.h
    compilationFiles: Optional[List[str]] = []


class Testcase(BaseModel):
    # The path of the input file, relative to the package directory.
    # In case this is given through a `testcasePattern`, this is a Python
    # regex that matches input file paths relative to the package directory.
    inputPath: str

    # The path of the output file, relative to the package directory.
    # In case this is given through a `testcasePattern`, this is a Python
    # regex that matches output file paths relative to the package directory.
    outputPath: str


class GeneratorCall(BaseModel):
    # The identifier of the generator to call.
    name: str

    # The args to pass to this generator.
    args: Optional[str] = None


class TestcaseGroup(BaseModel):
    # The name of this test group.
    name: Optional[str] = None

    # Testcases below will be added to this group in the order
    # they're defined, from `testcases` first to `generatorScript` last.

    # The path to testcases relative to the package directory
    # to add to this group.
    testcases: Optional[List[Testcase]] = []

    # A Python regex that matches input/output file paths relative to the
    # package directory. The matched files will be added to this group.
    testcasePattern: Optional[Testcase] = None

    # The generators to call to generate testcases for this group.
    generators: Optional[List[GeneratorCall]] = []

    # A generator script to call to generate testcases for this group.
    generatorScript: Optional[str] = None

    # A validator to use to validate the testcases of this group.
    # If not specified, will use the package-level validator.
    # Useful in cases where the constraints vary across test groups.
    validator: Optional[CodeItem] = None

    # The weight of this group in the final score. Useful for
    # problems that have points.
    weight: Optional[float] = 1.0


class Generator(CodeItem):
    # The name of this generator.
    # This can be further referenced in testcase groups and
    # stress tests.
    name: str


class Solution(CodeItem):
    # The expected outcome of this solution.
    outcome: ExpectedOutcome


class Package(BaseModel):
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
