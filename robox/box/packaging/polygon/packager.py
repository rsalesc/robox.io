import pathlib
import shutil
from typing import List

import iso639
import typer

from robox import console
from robox.box import package
from robox.box.packaging.packager import BasePackager, BuiltStatement
from robox.box.packaging.polygon import xml_schema as polygon_schema
from robox.config import get_testlib


def langs_to_code(langs: List[str]) -> List[str]:
    return [iso639.Language.from_name(lang).part1 for lang in langs]


def code_to_langs(langs: List[str]) -> List[str]:
    return [iso639.Language.from_part1(lang).name.lower() for lang in langs]


class PolygonPackager(BasePackager):
    def _validate(self):
        langs = self.languages()
        pkg = package.find_problem_package_or_die()

        lang_codes = set()
        for statement in pkg.statements:
            lang_codes.add(statement.title)

        for lang in langs:
            if lang not in lang_codes:
                console.console.print(
                    f'[error]No statement from language [item]{lang}[/item] found. '
                    'Polygon needs one statement for each language.[/error]'
                )
                raise typer.Exit(1)

    def _get_names(self) -> List[polygon_schema.Name]:
        return [
            polygon_schema.Name(
                language=code_to_langs([lang])[0],
                value=self.get_statement_for_language(lang).title,
            )
            for lang in self.languages()
        ]

    def _get_checker(self) -> polygon_schema.Checker:
        # TODO: support other checker languages
        return polygon_schema.Checker(
            name='robox::checker',
            type='testlib',
            source=polygon_schema.File(path='files/check.cpp', type='cpp.g++17'),
            cpy=polygon_schema.File(path='check.cpp'),
        )

    def _get_manual_test(self) -> polygon_schema.Test:
        # TODO: return samples
        return polygon_schema.Test(method='manual')

    def _get_single_testset(self) -> polygon_schema.Testset:
        pkg = package.find_problem_package_or_die()

        testcases = self.get_flattened_built_testcases()

        return polygon_schema.Testset(
            name='tests',
            timelimit=pkg.timeLimit,
            memorylimit=pkg.memoryLimit * 1024 * 1024,
            size=len(testcases),
            inputPattern='tests/%03d',
            answerPattern='tests/%03d.a',
            tests=[self._get_manual_test() for _ in range(len(testcases))],
        )

    def _get_judging(self) -> polygon_schema.Judging:
        return polygon_schema.Judging(testsets=[self._get_single_testset()])

    def _get_files(self) -> List[polygon_schema.File]:
        return [polygon_schema.File(path='files/testlib.h', type='h.g++')]

    def _statement_application_type(self, statement: BuiltStatement) -> str:
        return 'application/pdf'

    def _process_statement(
        self,
        built_statement: BuiltStatement,
        into_path: pathlib.Path,
    ) -> polygon_schema.Statement:
        language = code_to_langs([built_statement.statement.language])[0]
        final_path = (
            into_path
            / 'statements'
            / language
            / str(built_statement.output_type)
            / built_statement.path.name
        )

        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built_statement.path, final_path)

        return polygon_schema.Statement(
            path=str(built_statement.path),
            language=language,
            type=self._statement_application_type(built_statement),  # type: ignore
        )

    def _process_statements(
        self, into_path: pathlib.Path
    ) -> List[polygon_schema.Statement]:
        return [
            self._process_statement(built_statement, into_path)
            for built_statement in self.built_statements
        ]

    def name(self) -> str:
        return 'polygon'

    def package(self, build_path: pathlib.Path, into_path: pathlib.Path):
        problem = polygon_schema.Problem(
            names=self._get_names(),
            checker=self._get_checker(),
            judging=self._get_judging(),
            files=self._get_files(),
            statements=self._process_statements(into_path),
        )

        descriptor: str = problem.to_xml(
            skip_empty=True,
            encoding='utf-8',
            pretty_print=True,
            standalone=True,
        )  # type: ignore
        if isinstance(descriptor, bytes):
            descriptor = descriptor.decode()

        # Prepare files
        files_path = into_path / 'files'
        files_path.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(get_testlib(), files_path / 'testlib.h')
        shutil.copyfile(package.get_checker().path, files_path / 'check.cpp')
        shutil.copyfile(package.get_checker().path, into_path / 'check.cpp')

        # Copy all testcases
        (into_path / 'tests').mkdir(parents=True, exist_ok=True)
        testcases = self.get_flattened_built_testcases()
        for i, testcase in enumerate(testcases):
            shutil.copyfile(
                testcase.inputPath,
                into_path / f'tests/{i+1:03d}',
            )
            if testcase.outputPath is not None:
                shutil.copyfile(
                    testcase.outputPath,
                    into_path / f'tests/{i+1:03d}.a',
                )
            else:
                (into_path / f'tests/{i+1:03d}.a').touch()

        # Write problem.xml
        (into_path / 'problem.xml').write_text(descriptor)

        # Zip all.
        shutil.make_archive(str(build_path / 'problem'), 'zip', into_path)
