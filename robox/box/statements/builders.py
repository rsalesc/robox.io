import dataclasses
import pathlib
import shutil
import tempfile
import typing
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

import typer

from robox import console
from robox.box.schema import Package, Testcase
from robox.box.statements.latex import Latex
from robox.box.statements.latex_jinja import (
    render_latex_template,
    render_latex_template_blocks,
)
from robox.box.statements.schema import (
    JinjaTeX,
    PipelineStep,
    Statement,
    StatementType,
    TexToPDF,
    roboxToTeX,
)


@dataclasses.dataclass
class StatementCodeLanguage:
    name: str
    command: str


@dataclasses.dataclass
class StatementBuilderInput:
    id: str
    content: bytes
    languages: List[StatementCodeLanguage]
    package: Package
    statement: Statement
    samples: List[Testcase]
    params: PipelineStep
    assets: List[Tuple[pathlib.Path, pathlib.Path]] = dataclasses.field(
        default_factory=list
    )

    def build_jinja_kwargs(self) -> Dict[str, Any]:
        return {
            'languages': self.languages,
            'package': self.package,
            'statement': self.statement,
            'vars': self.package.vars,
        }


@dataclasses.dataclass
class StatementBuilderOutput:
    content: bytes


@dataclasses.dataclass
class ProblemWithStatement:
    package: Package
    statement: Statement
    blocks: Dict[str, str] = dataclasses.field(default_factory=dict)
    samples: List[Testcase] = dataclasses.field(default_factory=list)

    def has_block(self, block: str) -> bool:
        return block in self.blocks

    def get_block(self, block: str) -> str:
        return self.blocks[block]


def prepare_assets(
    assets: List[Tuple[pathlib.Path, pathlib.Path]],
    dest_dir: pathlib.Path,
):
    dest_dir.mkdir(parents=True, exist_ok=True)

    for asset_in, asset_out in assets:
        if not asset_in.is_file():
            console.console.print(
                f'[error]Asset [item]{asset_in}[/item] does not exist in your package.[/error]'
            )
            raise typer.Exit(1)

        # dest_path = dest_dir / asset.resolve().relative_to(statement_dir)
        dest_path = dest_dir / asset_out
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(asset_in), str(dest_path))


def render_jinja(
    assets: List[Tuple[pathlib.Path, pathlib.Path]], content: bytes, **kwargs
) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        temp_dir = pathlib.Path(td)
        prepare_assets(assets, temp_dir)

        temp_file = '__input__.tex'
        temp_path = temp_dir / temp_file
        temp_path.write_bytes(content)

        result: str = render_latex_template(
            str(temp_dir),
            temp_file,
            kwargs,
        )
        return result.encode()


def render_jinja_blocks(
    assets: List[Tuple[pathlib.Path, pathlib.Path]], content: bytes, **kwargs
) -> Dict[str, str]:
    with tempfile.TemporaryDirectory() as td:
        temp_dir = pathlib.Path(td)
        prepare_assets(assets, temp_dir)

        temp_file = '__input__.tex'
        temp_path = temp_dir / temp_file
        temp_path.write_bytes(content)

        result: Dict[str, str] = render_latex_template_blocks(
            str(temp_dir),
            temp_file,
            kwargs,
        )
        return result


class StatementBuilder(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def default_params(self) -> PipelineStep:
        pass

    @abstractmethod
    def input_type(self) -> StatementType:
        pass

    @abstractmethod
    def output_type(self) -> StatementType:
        pass

    def inject_assets(
        self, params: PipelineStep
    ) -> List[Tuple[pathlib.Path, pathlib.Path]]:
        return []

    @abstractmethod
    def build(
        self, input: StatementBuilderInput, verbose: bool = False
    ) -> StatementBuilderOutput:
        pass


class JinjaTeXBuilder(StatementBuilder):
    def name(self) -> str:
        return 'jinja-tex'

    def default_params(self) -> PipelineStep:
        return JinjaTeX(type='jinja-tex')

    def input_type(self) -> StatementType:
        return StatementType.JinjaTeX

    def output_type(self) -> StatementType:
        return StatementType.TeX

    def build(
        self, input: StatementBuilderInput, verbose: bool = False
    ) -> StatementBuilderOutput:
        return StatementBuilderOutput(
            content=render_jinja(
                input.assets,
                input.content,
                **input.build_jinja_kwargs(),
            )
        )


class roboxTeXBuilder(StatementBuilder):
    def name(self) -> str:
        return 'rbx-tex'

    def default_params(self) -> PipelineStep:
        return roboxToTeX(type='rbx-tex')

    def input_type(self) -> StatementType:
        return StatementType.roboxTeX

    def output_type(self) -> StatementType:
        return StatementType.TeX

    def inject_assets(
        self, params: PipelineStep
    ) -> List[Tuple[pathlib.Path, pathlib.Path]]:
        params = typing.cast(roboxToTeX, params)
        if not params.template:
            return []
        return [(params.template, params.template)]

    def build(
        self, input: StatementBuilderInput, verbose: bool = False
    ) -> StatementBuilderOutput:
        params = typing.cast(roboxToTeX, input.params)
        assert params.template is not None
        blocks = render_jinja_blocks(
            input.assets, input.content, **input.build_jinja_kwargs()
        )

        input_str = f'%- extends "{params.template}"'
        problems = [
            ProblemWithStatement(
                input.package, input.statement, blocks, samples=input.samples
            )
        ]
        return StatementBuilderOutput(
            content=render_jinja(
                input.assets,
                input_str.encode(),
                **input.build_jinja_kwargs(),
                problems=problems,
            )
        )


class TeX2PDFBuilder(StatementBuilder):
    def name(self) -> str:
        return 'tex2pdf'

    def default_params(self) -> PipelineStep:
        return TexToPDF(type='tex2pdf')

    def input_type(self) -> StatementType:
        return StatementType.TeX

    def output_type(self) -> StatementType:
        return StatementType.PDF

    def build(
        self, input: StatementBuilderInput, verbose: bool = False
    ) -> StatementBuilderOutput:
        latex = Latex(input.content.decode())
        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            prepare_assets(input.assets, temp_dir)
            latex_result = latex.build_pdf(temp_dir)
        pdf = latex_result.pdf
        if pdf is None:
            console.console.print(f'{latex_result.result.stdout.decode()}')
            console.console.print('[error]PdfLaTeX compilation failed.[/error]')
            raise typer.Exit(1)

        if verbose:
            console.console.print(f'{latex_result.result.stdout.decode()}')

        return StatementBuilderOutput(content=pdf)


BUILDER_LIST = [TeX2PDFBuilder(), JinjaTeXBuilder(), roboxTeXBuilder()]
