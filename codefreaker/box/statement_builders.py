import shutil
from abc import ABC, abstractmethod

import typer
from pdflatex import PDFLaTeX

from codefreaker import console
from codefreaker.box import package
from codefreaker.box.schema import Statement


class StatementBuilder(ABC):
    @abstractmethod
    def should_handle(self, statement: Statement) -> bool:
        pass

    @abstractmethod
    def build(self, statement: Statement, verbose: bool = False):
        pass


class PDFBuilder(StatementBuilder):
    def should_handle(self, statement: Statement) -> bool:
        return statement.params.type == 'pdf'

    def build(self, statement: Statement, verbose: bool = False):
        build_dir = package.get_build_path()
        build_dir.mkdir(parents=True, exist_ok=True)

        if not statement.params.path.is_file():
            console.console.print(
                f'[error]File [item]{statement.params.path}[/item] does not exist.[/error]',
            )
            raise typer.Exit(1)

        shutil.copyfile(
            str(statement.params.path),
            str(build_dir / f'statement.{statement.language}.pdf'),
        )


class TexBuilder(StatementBuilder):
    def should_handle(self, statement: Statement) -> bool:
        return statement.params.type == 'tex'

    def build(self, statement: Statement, verbose: bool = False):
        build_dir = package.get_build_path()
        build_dir.mkdir(parents=True, exist_ok=True)

        if not statement.params.path.is_file():
            console.console.print(
                f'[error]File [item]{statement.params.path}[/item] does not exist.[/error]',
            )
            raise typer.Exit(1)
        pdfl = PDFLaTeX.from_texfile(str(statement.params.path))
        pdf, log, fp = pdfl.create_pdf()
        if fp.returncode != 0:
            console.console.print(
                f'[error]Failed to compile TeX statement: {statement.params.path}[/error]',
            )
            console.console.print(fp.stdout.decode())
            raise typer.Exit(1)
        (build_dir / f'statement.{statement.language}.pdf').write_bytes(pdf)

        if verbose:
            console.console.print(log.decode())


BUILDER_LIST = [PDFBuilder(), TexBuilder()]
