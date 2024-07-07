import dataclasses
import pathlib
import typing
from typing import List, Optional, Set, Tuple

import typer

from robox import console, utils
from robox.box.contest import contest_utils
from robox.box.contest.contest_package import get_problems
from robox.box.contest.schema import Contest, ContestProblem, ContestStatement
from robox.box.schema import Package, Testcase
from robox.box.statements.build_statements import (
    get_builders,
    get_environment_languages_for_statement,
    get_relative_assets,
)
from robox.box.statements.builders import (
    StatementBuilderContest,
    StatementBuilderContext,
    StatementBuilderProblem,
)
from robox.box.statements.schema import Statement, StatementType
from robox.box.testcases import get_samples


@dataclasses.dataclass
class ExtractedProblem:
    package: Package
    statement: Statement
    problem: ContestProblem
    samples: List[Testcase]

    def get_statement_path(self) -> pathlib.Path:
        return self.problem.get_path() / self.statement.path

    def get_statement_assets(self) -> List[str]:
        return [str(self.problem.get_path() / asset) for asset in self.statement.assets]


def _get_samples(problem: ContestProblem) -> List[Testcase]:
    with utils.new_cd(problem.get_path()):
        contest_utils.clear_package_cache()
        return get_samples()


def get_problems_for_statement(
    contest: Contest, language: str
) -> List[ExtractedProblem]:
    pkgs = get_problems(contest)
    if not pkgs:
        console.console.print(
            '[error]No problems found in the contest, cannot infer statement type.[/error]'
        )
        raise typer.Exit(1)

    res = []
    for pkg, problem in zip(pkgs, contest.problems):
        found = False
        for statement in pkg.statements:
            if statement.language == language:
                found = True
                res.append(
                    ExtractedProblem(
                        package=pkg,
                        statement=statement,
                        problem=problem,
                        samples=_get_samples(problem),
                    )
                )
                break
        if not found:
            console.console.print(
                f'[error]No statement found for language {language} in problem {problem.short_name}[/error]'
            )
            raise typer.Exit(1)

    return res


def get_common_type(extracted_problems: List[ExtractedProblem]) -> StatementType:
    all_types: Set[StatementType] = set()
    for extracted_problem in extracted_problems:
        all_types.add(extracted_problem.statement.type)
    if len(all_types) > 1:
        console.console.print(
            '[error]Multiple statement types found in the contest, cannot infer common type.[/error]'
        )
        raise typer.Exit(1)
    return all_types.pop()


def get_builder_problems(
    extracted_problems: List[ExtractedProblem],
) -> List[StatementBuilderProblem]:
    return [
        StatementBuilderProblem(
            package=ex.package,
            statement=ex.statement,
            samples=ex.samples,
        )
        for ex in extracted_problems
    ]


def _get_problem_level_relative_assets(
    extracted_problems: List[ExtractedProblem],
) -> List[Tuple[pathlib.Path, pathlib.Path]]:
    assets = []
    for extracted_problem in extracted_problems:
        assets.extend(
            get_relative_assets(
                extracted_problem.get_statement_path(),
                extracted_problem.get_statement_assets(),
            )
        )
    dest_assets = set()
    for asset in assets:
        if asset[1] in dest_assets:
            console.console.print(
                f'[warning]Duplicate asset [item]{asset[1]}[/item] found in the contest.[/warning]'
            )
            raise typer.Exit(1)
        dest_assets.add(asset[1])
    return assets


def build_statement(
    statement: ContestStatement,
    contest: Contest,
    output_type: Optional[StatementType] = None,
) -> pathlib.Path:
    extracted_problems = get_problems_for_statement(contest, statement.language)
    common_type = get_common_type(extracted_problems)
    builders = get_builders(
        str(contest.name),
        statement.steps,
        statement.configure,
        common_type,
        output_type,
    )
    last_output = common_type
    last_content = [
        extracted_problem.get_statement_path().read_bytes()
        for extracted_problem in extracted_problems
    ]
    for bdr, params in builders:
        assets = (
            get_relative_assets(pathlib.Path(), statement.assets)
            + _get_problem_level_relative_assets(extracted_problems)
            + bdr.inject_assets(params)
        )
        output = bdr.build(
            input=last_content,
            context=StatementBuilderContext(
                languages=get_environment_languages_for_statement(),
                params=params,
                assets=assets,
            ),
            item=StatementBuilderContest(
                information=contest.information[statement.language],
                problems=get_builder_problems(extracted_problems),
            ),
            verbose=False,
        )
        last_output = bdr.output_type()
        last_content = output

    statement_path = pathlib.Path(f'statement{last_output.get_file_suffix()}')
    statement_path.parent.mkdir(parents=True, exist_ok=True)
    statement_path.write_bytes(typing.cast(bytes, last_content))
    console.console.print(
        f'Statement built successfully for language '
        f'[item]{statement.language}[/item] at '
        f'[item]{statement_path}[/item].'
    )
    return statement_path
