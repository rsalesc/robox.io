import dataclasses
from abc import ABC, abstractmethod

import typer
from pdflatex import PDFLaTeX

from codefreaker import console
from codefreaker.box import statement_schema


@dataclasses.dataclass
class StatementBuilderInput:
    id: str
    content: bytes


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
        pdfl = PDFLaTeX.from_binarystring(input.content, self.name())  # type: ignore
        pdf, log, fp = pdfl.create_pdf()
        if fp.returncode != 0:
            console.console.print(
                f'[error]Failed to compile TeX statement: [item]{input.id}[/item][/error]',
            )
            console.console.print(fp.stdout.decode())
            raise typer.Exit(1)

        if verbose:
            console.console.print(log.decode())
        return StatementBuilderOutput(content=pdf)


BUILDER_LIST = [TeX2PDFBuilder()]
