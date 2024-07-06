import pathlib
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from robox.box.schema import NameField
from robox.box.statements.schema import ConversionStep


def ShortNameField(**kwargs):
    return Field(pattern=r'^[A-Z]+[0-9]*$', min_length=1, max_length=4, **kwargs)


class ContestStatements(BaseModel):
    steps: List[ConversionStep] = Field(
        [],
        discriminator='type',
        description="""
Describes a sequence of conversion steps that should be applied to the statement file of
problems in this contest.

Usually, it is not necessary to specify these, as they can be inferred from the
input statement type and the output statement type, but you can use this to force
certain conversion steps to happen.
""",
    )

    configure: List[ConversionStep] = Field(
        [],
        discriminator='type',
        description="""
Configure how certain conversion steps should happen when applied to the statement files of
problems in this contest.

Different from the `steps` field, this does not force the steps to happen, but rather only
configure them in case they are applied.
""",
    )

    assets: List[str] = Field(
        [],
        description="""
Assets relative to the contest directory that should be included while building
the statement. Files will be included in the same folder as the statement file.
Can be glob pattern as well, such as `imgs/*.png`.
""",
    )


class ContestProblem(BaseModel):
    short_name: str = ShortNameField(
        description="""
Short name of the problem. Usually, just an uppercase letter,
but can be a sequence of uppercase letters followed by a number."""
    )
    path: pathlib.Path = Field(
        description="""
Path to the problem relative to the contest package directory.
If not specified, will expect the problem to be in ./{short_name}/ folder."""
    )

    color: Optional[str] = Field(
        description="""Hex-based color that represents this problem in the contest.""",
        pattern=r'^[A-Za-z0-9]+$',
        max_length=6,
    )


class Contest(BaseModel):
    name: str = NameField(description='Name of this contest.')

    titles: Dict[str, str] = Field(
        {}, description='Human-readable nome of the contest per language.'
    )

    problems: List[ContestProblem] = Field(
        [], description='List of problems in this contest.'
    )

    statements: Optional[ContestStatements] = Field(
        None,
        description='Override statement configuration for problems in this contest.',
    )
