import pathlib
from typing import Optional

from rbx import annotations, console, metadata
from rbx.config import get_config, open_editor


def main(problem: str, language: Optional[annotations.LanguageWithDefault] = None):
    lang = get_config().get_language(language)
    if lang is None:
        console.console.print(
            f'[error]Language {language or get_config().defaultLanguage} not found in config. Please check your configuration.[/error]'
        )
        return

    dumped_problem = metadata.find_problem_by_anything(problem)
    if not dumped_problem:
        console.console.print(
            f'[error]Problem with identifier {problem} not found.[/error]'
        )
        return

    filename = lang.get_file(dumped_problem.code)
    open_editor(pathlib.Path(filename))
