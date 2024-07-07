import pathlib
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from robox.box.schema import NameField
from robox.box.statements.schema import ConversionStep


def ShortNameField(**kwargs):
    return Field(pattern=r'^[A-Z]+[0-9]*$', min_length=1, max_length=4, **kwargs)


class ContestStatement(BaseModel):
    language: str = Field('en', description='Language code for this statement.')

    steps: List[ConversionStep] = Field(
        default=[],
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
        default=[],
        discriminator='type',
        description="""
Configure how certain conversion steps should happen when applied to the statement files of
problems in this contest.

Different from the `steps` field, this does not force the steps to happen, but rather only
configure them in case they are applied.
""",
    )

    assets: List[str] = Field(
        default=[],
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
    path: Optional[pathlib.Path] = Field(
        default=None,
        description="""
Path to the problem relative to the contest package directory.
If not specified, will expect the problem to be in ./{short_name}/ folder.""",
    )

    color: Optional[str] = Field(
        default=None,
        description="""Hex-based color that represents this problem in the contest.""",
        pattern=r'^[A-Za-z0-9]+$',
        max_length=6,
    )

    def get_path(self) -> pathlib.Path:
        return self.path or pathlib.Path(self.short_name)


class ContestInformation(BaseModel):
    title: str = Field(description='Title of the contest in this language.')

    location: Optional[str] = Field(
        default=None, description='Location of the contest in this language.'
    )

    date: Optional[str] = Field(
        default=None, description='Date of the contest in this language.'
    )


class Contest(BaseModel):
    name: str = NameField(description='Name of this contest.')

    information: Dict[str, ContestInformation] = Field(
        default={},
        description='Human-readable information of the contest per language.',
    )

    problems: List[ContestProblem] = Field(
        default=[], description='List of problems in this contest.'
    )

    statements: List[ContestStatement] = Field(
        default=None,
        description='Override statement configuration for problems in this contest, per language.',
    )
