import pathlib
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

from codefreaker.autoenum import AutoEnum, alias


### Pipeline nodes.
class CodefreakerToTeX(BaseModel):
    type: Literal['cfk-tex']


class TexToPDF(BaseModel):
    type: Literal['tex2pdf']


class JinjaTeX(BaseModel):
    type: Literal['jinja-tex']


PipelineStep = TexToPDF | JinjaTeX


### Statement types
class StatementType(AutoEnum):
    CodefreakerTeX = alias('codefreaker-tex', 'cfk-tex')  # type: ignore
    TeX = alias('tex')
    JinjaTeX = alias('jinja-tex')
    PDF = alias('pdf')

    def get_file_suffix(self) -> str:
        match self:
            case StatementType.TeX:
                return '.tex'
            case StatementType.CodefreakerTeX:
                return '.cfk.tex'
            case StatementType.JinjaTeX:
                return '.jinja.tex'
            case StatementType.PDF:
                return '.pdf'
        raise ValueError(f'Unknown statement type: {self}')


class Statement(BaseModel):
    model_config = ConfigDict(extra='forbid')

    path: pathlib.Path
    type: StatementType

    pipeline: List[PipelineStep] = Field(default_factory=list, discriminator='type')
    assets: List[pathlib.Path] = []

    # Language this is statement is written in.
    language: str = 'en'
