import dataclasses
import pathlib
import tempfile
from abc import ABC, abstractmethod

import typer
from latexbuild import render_latex_template

from codefreaker import console
from codefreaker.box import statement_schema
from codefreaker.box.latex import Latex
from codefreaker.box.schema import Package


@dataclasses.dataclass
class StatementBuilderInput:
    id: str
    content: bytes
    package: Package


@dataclasses.dataclass
class StatementBuilderOutput:
    content: bytes


class StatementBuilder(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def input_type(self) -> statement_schema.StatementType:
        pass

    @abstractmethod
    def output_type(self) -> statement_schema.StatementType:
        pass

    @abstractmethod
    def build(
        self, input: StatementBuilderInput, verbose: bool = False
    ) -> StatementBuilderOutput:
        pass


class JinjaTeXBuilder(StatementBuilder):
    def name(self) -> str:
        return 'jinja-tex'

    def input_type(self) -> statement_schema.StatementType:
        return statement_schema.StatementType.JinjaTeX

    def output_type(self) -> statement_schema.StatementType:
        return statement_schema.StatementType.TeX

    def build(
        self, input: StatementBuilderInput, verbose: bool = False
    ) -> StatementBuilderOutput:
        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            temp_file = 'input.tex'
            temp_path = temp_dir / temp_file
            temp_path.write_bytes(input.content)

            result: str = render_latex_template(
                str(temp_dir), temp_file, {'package': input.package}
            )
            return StatementBuilderOutput(content=result.encode())


class TeX2PDFBuilder(StatementBuilder):
    def name(self) -> str:
        return 'tex2pdf'

    def input_type(self) -> statement_schema.StatementType:
        return statement_schema.StatementType.TeX

    def output_type(self) -> statement_schema.StatementType:
        return statement_schema.StatementType.PDF

    def build(
        self, input: StatementBuilderInput, verbose: bool = False
    ) -> StatementBuilderOutput:
        latex = Latex(input.content.decode())
        latex_result = latex.build_pdf()
        pdf = latex_result.pdf
        if pdf is None:
            console.console.print(f'{latex_result.result.stdout.decode()}')
            console.console.print('[error]PdfLaTeX compilation failed.[/error]')
            raise typer.Exit(1)

        if verbose:
            console.console.print(f'{latex_result.result.stdout.decode()}')

        return StatementBuilderOutput(content=pdf)


BUILDER_LIST = [TeX2PDFBuilder(), JinjaTeXBuilder()]
