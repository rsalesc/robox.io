from typing import Annotated, List, Optional

import typer

from robox import annotations, console, utils
from robox.box import builder, environment
from robox.box.contest import contest_utils
from robox.box.contest.build_contest_statements import build_statement
from robox.box.contest.contest_package import find_contest_package_or_die
from robox.box.statements.schema import StatementType

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


@app.command('build, b', help='Build statements.')
def build(
    verification: environment.VerificationParam,
    languages: Annotated[
        Optional[List[str]],
        typer.Option(
            default_factory=list,
            help='Languages to build statements for. If not specified, build statements for all available languages.',
        ),
    ],
    output: Annotated[
        Optional[StatementType],
        typer.Option(
            case_sensitive=False,
            help='Output type to be generated. If not specified, will infer from the conversion steps specified in the package.',
        ),
    ] = StatementType.PDF,
    samples: Annotated[
        bool,
        typer.Option(
            help='Whether to build the statement with samples or not.'
        ),
    ] = True,
):
    contest = find_contest_package_or_die()
    # At most run the validators, only in samples.
    if samples:
        for problem in contest.problems:
            console.console.print(
                f'Processing problem [item]{problem.short_name}[/item]...'
            )
            with utils.new_cd(problem.get_path()):
                contest_utils.clear_package_cache()
                builder.build(verification=verification, groups=set(['samples']))

    contest = find_contest_package_or_die()
    candidate_languages = languages
    if not candidate_languages:
        candidate_languages = sorted(set([st.language for st in contest.statements]))

    for language in candidate_languages:
        candidates_for_lang = [
            st for st in contest.statements if st.language == language
        ]
        if not candidates_for_lang:
            console.console.print(
                f'[error]No contest-level statement found for language [item]{language}[/item].[/error]',
            )
            raise typer.Exit(1)

        build_statement(candidates_for_lang[0], contest, output_type=output, use_samples=samples)


@app.callback()
def callback():
    pass
