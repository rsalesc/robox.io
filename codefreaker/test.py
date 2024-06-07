import atexit
import typer

from codefreaker import annotations, metadata
from codefreaker.config import get_config
from codefreaker.console import console
from codefreaker.grading import steps
from codefreaker.grading.judge.sandboxes import stupid_sandbox


def main(
    problem: annotations.Problem,
    language: annotations.LanguageWithDefault = None,
    keep_sandbox: bool = False,
):
    dumped_problem = metadata.find_problem_by_anything(problem)
    if not dumped_problem:
        console.print(
            f"[error]Problem with identifier [item]{problem}[/item] not found.[/error]"
        )
        return

    lang = get_config().get_language(language)
    if not lang:
        console.print(
            f"[error]Language {language or get_config().defaultLanguage} not found in config. Please check your configuration.[/error]"
        )
        return

    box = stupid_sandbox.StupidSandbox()
    atexit.register(lambda: box.cleanup(delete=not keep_sandbox))

    if not steps.preprocess(dumped_problem, lang, box):
        console.print(
            f"[error]Failed to preprocess problem [item]{dumped_problem.pretty_name()}[/item].[/error]"
        )
