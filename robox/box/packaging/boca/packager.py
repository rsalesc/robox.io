import pathlib
import shutil

import typer

from robox import console
from robox.box import package
from robox.box.packaging.packager import BasePackager, BuiltStatement
from robox.box.statements.schema import Statement


class BocaPackager(BasePackager):
    def _get_main_statement(self) -> Statement:
        pkg = package.find_problem_package_or_die()

        if not pkg.statements:
            console.console.print('[error]No statements found.[/error]')
            raise typer.Exit(1)

        return pkg.statements[0]

    def _get_main_built_statement(self) -> BuiltStatement:
        statement = self._get_main_statement()
        for built_statement in self.built_statements:
            if built_statement.statement == statement:
                return built_statement

        console.console.print(
            '[error]Main statement not found among built statements.[/error]'
        )
        raise typer.Exit(1)

    def _get_problem_name(self) -> str:
        pkg = package.find_problem_package_or_die()
        return pkg.name

    def _get_problem_info(self) -> str:
        statement = self._get_main_statement()
        return (
            'basename=A\n'
            f'fullname={statement.title}\n'
            f'descfile={self._get_problem_name()}.pdf\n'
        )

    def name(self) -> str:
        return 'boca'

    def package(self, build_path: pathlib.Path, into_path: pathlib.Path):
        # Problem statement
        description_path = into_path / 'description'
        description_path.mkdir(parents=True, exist_ok=True)
        (description_path / 'problem.info').write_text(self._get_problem_info())
        shutil.copyfile(
            self._get_main_built_statement().path,
            (description_path / self._get_problem_name()).with_suffix('.pdf'),
        )

        # Prepare IO
        inputs_path = into_path / 'input'
        inputs_path.mkdir(parents=True, exist_ok=True)
        outputs_path = into_path / 'output'
        outputs_path.mkdir(parents=True, exist_ok=True)

        testcases = self.get_flattened_built_testcases()
        for i, testcase in enumerate(testcases):
            shutil.copyfile(testcase.inputPath, inputs_path / f'{i+1:03d}')
            if testcase.outputPath is not None:
                shutil.copyfile(testcase.outputPath, outputs_path / f'{i+1:03d}')
            else:
                (outputs_path / f'{i+1:03d}').touch()

        # Zip all.
        shutil.make_archive(
            str(build_path / self._get_problem_name()), 'zip', into_path
        )
