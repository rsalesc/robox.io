import atexit
import os
import shlex

from rbx import annotations, grading_utils, metadata
from rbx.config import get_config
from rbx.console import stderr_console
from rbx.grading import steps
from rbx.grading.judge.sandboxes import stupid_sandbox


def main(
    problem: annotations.Problem,
    language: annotations.LanguageWithDefault = None,
    keep_sandbox: bool = False,
):
    dumped_problem = metadata.find_problem_by_anything(problem)
    if not dumped_problem:
        stderr_console.print(
            f'[error]Problem with identifier [item]{problem}[/item] not found.[/error]'
        )
        return

    lang = get_config().get_language(language)
    if not lang:
        stderr_console.print(
            f'[error]Language {language or get_config().defaultLanguage} not found in config. Please check your configuration.[/error]'
        )
        return

    box = stupid_sandbox.StupidSandbox()
    atexit.register(lambda: box.cleanup(delete=not keep_sandbox))

    preprocess_cmds = grading_utils.build_preprocess_commands(dumped_problem, lang)
    sandbox_params = grading_utils.build_preprocess_sandbox_params()
    artifacts = grading_utils.build_compile_grading_artifacts(dumped_problem, lang)

    if not steps.compile(preprocess_cmds, sandbox_params, box, artifacts):
        stderr_console.print(
            f'[error]Failed to preprocess problem [item]{dumped_problem.pretty_name()}[/item].[/error]'
        )
        return

    cmd = shlex.split(lang.exec)
    os.execv(cmd[0], cmd)
