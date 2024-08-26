from __future__ import annotations

import pathlib
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from robox.autoenum import AutoEnum, alias
from robox.box.statements.schema import Statement
from robox.grading.steps import Outcome

Primitive = Union[str, int, float, bool]


def NameField(**kwargs):
    return Field(
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9\-]*$', min_length=3, max_length=32, **kwargs
    )


def _expand_var(value: Primitive) -> Primitive:
    if not isinstance(value, str):
        return value
    if value.startswith('\\'):
        return value[1:]
    if not value.startswith('py`') or not value.endswith('`'):
        return value
    res = eval(value[3:-1])
    for supported_type in [str, int, float, bool]:
        if isinstance(res, supported_type):
            return res

    raise TypeError(
        f'Variable with backticks should evaluate to a primitive Python type: {value}'
    )


class ExpectedOutcome(AutoEnum):
    ACCEPTED = alias('accepted', 'ac', 'correct')  # type: ignore
    """Expected outcome for correct solutions (AC)."""

    WRONG_ANSWER = alias('wrong answer', 'wa')  # type: ignore
    """Expected outcome for solutions that finish successfully,
    but the produced output are incorrect (WA)."""

    INCORRECT = alias('fail', 'incorrect')  # type: ignore
    """Expected outcome for solutions that finish with any non-AC verdict."""

    RUNTIME_ERROR = alias('runtime error', 'rte', 're')  # type: ignore
    """Expected outcome solutions that finish with non-zero code (RTE)."""

    TIME_LIMIT_EXCEEDED = alias('time limit exceeded', 'timeout', 'tle')  # type: ignore
    """Expected outcome for solutions that do not finish in time."""

    MEMORY_LIMIT_EXCEEDED = alias('memory limit exceeded', 'mle')  # type: ignore
    """Expected outcome for solutions that use more memory than allowed."""

    TLE_OR_RTE = alias('tle or rte', 'tle/rte', 'tle+rte')  # type: ignore
    """Expected outcome for solutions that finish with either TLE or RTE.
    
    Especially useful for environments where TLE and RTE are indistinguishable."""

    def match(self, outcome: Outcome) -> bool:
        if self == ExpectedOutcome.ACCEPTED:
            return outcome == Outcome.ACCEPTED
        if self == ExpectedOutcome.WRONG_ANSWER:
            return outcome == Outcome.WRONG_ANSWER
        if self == ExpectedOutcome.INCORRECT:
            return outcome in {
                Outcome.WRONG_ANSWER,
                Outcome.RUNTIME_ERROR,
                Outcome.MEMORY_LIMIT_EXCEEDED,
                Outcome.TIME_LIMIT_EXCEEDED,
            }
        if self == ExpectedOutcome.RUNTIME_ERROR:
            return outcome == Outcome.RUNTIME_ERROR
        if self == ExpectedOutcome.TIME_LIMIT_EXCEEDED:
            return outcome == Outcome.TIME_LIMIT_EXCEEDED
        if self == ExpectedOutcome.MEMORY_LIMIT_EXCEEDED:
            return outcome == Outcome.MEMORY_LIMIT_EXCEEDED
        if self == ExpectedOutcome.TLE_OR_RTE:
            return outcome in {Outcome.TIME_LIMIT_EXCEEDED, Outcome.RUNTIME_ERROR}
        return False


class CodeItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    path: pathlib.Path = Field(
        description="""The path to the code file, relative to the package directory."""
    )

    language: Optional[str] = Field(
        None, description="""The language of the code file."""
    )

    compilationFiles: Optional[List[str]] = Field(
        [],
        description="""
Extra files that should be placed alongside the code file during its compilation,
such as testlib.h, jngen.h, etc.

The paths should be given relative to the package directory, but will be included
relative to the `path` directory.

Testlib and jngen are already included by default.
""",
    )


class Testcase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    inputPath: pathlib.Path = Field(description="""The path of the input file.""")

    outputPath: Optional[pathlib.Path] = Field(
        None, description="""The path of the output file."""
    )


class GeneratorCall(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = NameField(description='The name of the generator to call.')

    args: Optional[str] = Field(
        None, description='The arguments to pass to the generator.'
    )


class TestcaseGroup(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = NameField(description='The name of the test group.')

    # Testcases below will be added to this group in the order
    # they're defined, from `testcases` first to `generatorScript` last.

    testcases: List[Testcase] = Field(
        [],
        description="""
The path of testcases to add to this group,
in the order they're defined.""",
    )

    testcaseGlob: Optional[str] = Field(
        None,
        description="""
A Python glob that matches input file paths relative to the
package directory. The globbed files should end with the extension
".in", and their corresponding outputs, if defined, should have the same file name,
but ending with ".out".
""",
    )

    generators: List[GeneratorCall] = Field(
        [],
        description="""
A list of generators to call to generate testcases for this group.
""",
    )

    generatorScript: Optional[CodeItem] = Field(
        None,
        description="""
A generator script to call to generate testcases for this group.
""",
    )

    validator: Optional[CodeItem] = Field(
        None,
        description="""
A validator to use to validate the testcases of this group.
If not specified, will use the package-level validator.
Useful in cases where the constraints vary across test groups.
""",
    )

    weight: Optional[float] = Field(
        1.0,
        description="""
The weight of this group in the final score. Useful for
problems that have points.
""",
    )


class Generator(CodeItem):
    model_config = ConfigDict(extra='forbid')

    name: str = NameField(description="""The name of the generator.""")


class Solution(CodeItem):
    model_config = ConfigDict(extra='forbid')

    outcome: ExpectedOutcome = Field(
        description="""The expected outcome of this solution."""
    )


class Stress(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = NameField(description='The name of the stress test.')

    generator: GeneratorCall = Field(
        description='Generator pattern to call during stress-test.'
    )

    solutions: List[str] = Field(
        [],
        description="""
Path of the solutions to be stress-tested.

If empty, will stress-test only the main solution for
non-WA verdicts.""",
    )

    outcome: ExpectedOutcome = Field(
        ExpectedOutcome.INCORRECT,
        description="""
What verdict to look for while stress-testing.
                                     """,
    )


class Package(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Name of the problem.
    name: str = NameField(description='The name of the problem.')

    timeLimit: int = Field(description='Time limit of the problem, in milliseconds.')

    memoryLimit: int = Field(description='Memory limit of the problem, in MB.')

    checker: Optional[CodeItem] = Field(
        None, description='The checker for this problem.'
    )

    validator: Optional[CodeItem] = Field(
        None, description='The validator for this problem.'
    )

    generators: List[Generator] = Field([], description='Generators for this problem.')

    solutions: List[Solution] = Field(
        [],
        description="""
All tested solutions for this problem.

The first solution in this list should be the main solution -- the one
that is correct and used as reference -- and should have the `accepted` outcome.
""",
    )

    testcases: List[TestcaseGroup] = Field([], description='Testcases for the problem.')

    stresses: List[Stress] = Field([], description='Stress tests for the problem.')

    statements: List[Statement] = Field([], description='Statements for the problem.')

    # Vars to be re-used across the package.
    #   - It will be passed as --key=value arguments to the validator.
    #   - It will be available as \VAR{key} variables in the robox statement.
    vars: Dict[str, Primitive] = Field(
        {}, description='Variables to be re-used across the package.'
    )

    @property
    def expanded_vars(self) -> Dict[str, Primitive]:
        return {key: _expand_var(value) for key, value in self.vars.items()}

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
