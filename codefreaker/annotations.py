from typing import Optional
import typer
from typing_extensions import Annotated

from .config import get_config

def _get_language_options():
    return list(get_config().languages.keys())

def _get_language_default():
    return get_config().defaultLanguage


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
