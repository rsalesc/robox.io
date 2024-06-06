from typing import Optional
import typer
from typing_extensions import Annotated

from .config import get_config
from . import metadata


def _get_language_options():
    return sorted(get_config().languages.keys())


def _get_language_default():
    return get_config().defaultLanguage


def _get_problem_options():
    options = set()
    all_problems = metadata.find_problems()
    for problem in all_problems:
        options.add(problem.code)
        options.update(problem.aliases)
    return sorted(options)


Timelimit = Annotated[
    Optional[int],
    typer.Option(
        "--timelimit",
        "-t",
        help="Time limit in milliseconds.",
        prompt="Time limit (ms)",
    ),
]
Memorylimit = Annotated[
    Optional[int],
    typer.Option(
        "--memorylimit",
        "-m",
        help="Memory limit in megabytes.",
        prompt="Memory limit (MB)",
    ),
]
Language = Annotated[
    str,
    typer.Option(
        "--language",
        "--lang",
        "-l",
        help="Language to use.",
        prompt="Language",
        default_factory=_get_language_default,
        autocompletion=_get_language_options,
    ),
]
Problem = Annotated[
    str,
    typer.Argument(autocompletion=_get_problem_options)
]

ProblemOption = Annotated[
    Optional[str],
    typer.Option("--problem", "-p", autocompletion=_get_problem_options)
]
