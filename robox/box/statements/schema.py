from __future__ import annotations

import pathlib
from typing import List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from robox.autoenum import AutoEnum, alias


### Pipeline nodes.
class roboxToTeX(BaseModel):
    """Configures the conversion between roboxTeX and LaTeX."""

    type: Literal['rbx-tex']

    template: pathlib.Path = Field(
        default=pathlib.Path('template.rbx.tex'),
        description='Path to the template that should be used to render the rbx-tex blocks.',
    )


class TexToPDF(BaseModel):
    """Configures the conversion between LaTeX and PDF using pdfLaTeX."""

    type: Literal['tex2pdf']


class JinjaTeX(BaseModel):
    type: Literal['jinja-tex']


PipelineStep = Union[TexToPDF, JinjaTeX, roboxToTeX]


### Statement types
class StatementType(AutoEnum):
    roboxTeX = alias('robox-tex', 'rbx-tex', 'rbx')  # type: ignore
    """Statement written in roboxTeX format."""

    TeX = alias('tex')
    """Statement written in pure LaTeX format."""

    JinjaTeX = alias('jinja-tex')
    """Statement written in LaTeX format with Jinja2 expressions."""

    PDF = alias('pdf')
    """Statement is a PDF."""

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

    pipeline: List[PipelineStep] = Field(
        default_factory=list,
        discriminator='type',
        description="""
Describes a sequence of conversion steps that should be applied to the statement file.

Usually, it is not necessary to specify these, as they can be inferred from the
input statement type and the output statement type, but you can use this to configure
how the conversion steps happen.
""",
    )

    assets: List[str] = Field(
        [],
        description="""
Assets relative to the package directory that should be included while building
the statement. Files will be included in the same folder as the statement file, preserving
their relativeness. Can be glob pattern as well, such as `imgs/*.png`.
""",
    )

    language: str = Field('en', description='Language this is statement is written in.')
