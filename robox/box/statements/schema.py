from __future__ import annotations

import pathlib
from typing import List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from robox.autoenum import AutoEnum, alias


### Pipeline nodes.
class roboxToTeX(BaseModel):
    type: Literal['rbx-tex']

    template: pathlib.Path = Field(
        pathlib.Path('template.rbx.tex'),
        description='Path to the template that should be used to render the rbx-tex blocks.',
    )


class TexToPDF(BaseModel):
    type: Literal['tex2pdf']


class JinjaTeX(BaseModel):
    type: Literal['jinja-tex']


PipelineStep = Union[TexToPDF, JinjaTeX, roboxToTeX]


### Statement types
class StatementType(AutoEnum):
    roboxTeX = alias('robox-tex', 'rbx-tex', 'rbx')  # type: ignore
    TeX = alias('tex')
    JinjaTeX = alias('jinja-tex')
    PDF = alias('pdf')

    def get_file_suffix(self) -> str:
        if self == StatementType.TeX:
            return '.tex'
        if self == StatementType.roboxTeX:
            return '.rbx.tex'
        if self == StatementType.JinjaTeX:
            return '.jinja.tex'
        if self == StatementType.PDF:
            return '.pdf'
        raise ValueError(f'Unknown statement type: {self}')


class Statement(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str = Field(
        description='Name of the problem, as it appears in the statement.'
    )

    path: pathlib.Path = Field(description='Path to the input statement file.')

    type: StatementType = Field(description='Type of the input statement file.')

    # Forces a certain sequence of conversion steps to happen during the statement
    # generation process.
    pipeline: List[PipelineStep] = Field(default_factory=list, discriminator='type')

    assets: List[str] = Field(
        [],
        description="""
Assets relative to the package directory that should be included while building
the statement. Files will be included in the same folder as the statement file, preserving
their relativeness. Can be glob pattern as well, such as `imgs/*.png`.
""",
    )

    language: str = Field('en', description='Language this is statement is written in.')
