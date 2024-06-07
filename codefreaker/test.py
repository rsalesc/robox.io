import atexit
import dataclasses
import pathlib
from typing import List
import typer

from codefreaker import annotations, metadata
from codefreaker.config import get_config
from codefreaker.console import console
from codefreaker.grading import steps
from codefreaker.grading.judge.sandboxes import stupid_sandbox
from codefreaker.schema import DumpedProblem


def get_testcase_index(path: pathlib.Path) -> int:
    return int(path.stem.split(".")[-1])


def get_testcases_io(
    problem: DumpedProblem, root: pathlib.Path = pathlib.Path(".")
) -> List[steps.TestcaseIO]:
    testcases_per_index = {}
    for input_file in root.glob(f"{problem.code}.*.in"):
        try:
            index = get_testcase_index(input_file)
        except ValueError:
            continue
        testcases_per_index[index] = steps.TestcaseIO(index=index, input=input_file)

    for output_file in root.glob(f"{problem.code}.*.out"):
        index = get_testcase_index(output_file)
        try:
            index = get_testcase_index(output_file)
        except ValueError:
            continue
        if index in testcases_per_index:
            testcases_per_index[index] = dataclasses.replace(
                testcases_per_index[index], output=output_file
            )
            continue
        testcases_per_index[index] = steps.TestcaseIO(index=index, output=output_file)

    return sorted(testcases_per_index.values(), key=lambda x: x.index)


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
        return

    testcases = get_testcases_io(dumped_problem)
    persist_root = pathlib.Path("persist")

    testcase_logs = steps.run(lang, box, testcases, persist_root)

    console.print(steps.evaluate(box, testcases, testcase_logs, persist_root))
