import atexit
import dataclasses
import pathlib
from typing import List, Optional
import rich
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.measure import Measurement, measure_renderables
import typer

from codefreaker import annotations, metadata, testcase_rendering
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


def _pretty_print_output_on_panel(file: pathlib.Path, title: str) -> Panel:
    return Panel(
        testcase_rendering.render_from_file(file),
        title=title,
        expand=False,
    )


def _pretty_print_side_by_side(result: steps.TestcaseEvaluation):
    return Columns(
        [
            _pretty_print_output_on_panel(result.testcase.output, "Expected"),
            _pretty_print_output_on_panel(result.log.stdout_absolute_path, "Actual"),
        ],
        equal=True,
        expand=False,
    )


def _pretty_print_outcome_panel(
    problem: DumpedProblem, result: steps.TestcaseEvaluation
) -> Panel:
    is_tle = result.outcome == steps.Outcome.TIME_LIMIT_EXCEEDED or (
        problem.timeLimit and result.log.time * 1000 > problem.timeLimit
    )

    text = Text()
    text.append("Outcome: ")
    text.append(
        result.outcome.value,
        style="success" if result.outcome == steps.Outcome.ACCEPTED else "error",
    )
    text.append(" " * 4)
    text.append("Time: ")
    text.append(f"{result.log.time:.2f}s", style="error" if is_tle else "item")
    text.append("\n")
    if result.testcase.input:
        text.append(f"Input path: {result.testcase.input.absolute()}")
        text.append("\n")
    if result.testcase.output:
        text.append(f"Expected path: {result.testcase.output.absolute()}")
        text.append("\n")
    text.append(f"Answer path: {result.log.stdout_absolute_path}")
    return Panel(
        text,
        title=f"[bold]Testcase [item]#{result.testcase.index}[/item]",
        expand=False,
    )


def _pretty_print_evaluation_result(
    problem: DumpedProblem, result: steps.TestcaseEvaluation
):
    console.print(_pretty_print_outcome_panel(problem, result))
    if result.outcome != steps.Outcome.ACCEPTED:
        console.print(_pretty_print_side_by_side(result))
    console.print()


def pretty_print_evaluation_results(
    problem: DumpedProblem, results: List[steps.TestcaseEvaluation]
):
    for result in results:
        _pretty_print_evaluation_result(problem, result)


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

    if not testcase_logs:
        console.print(
            f"[error]Failed to run testcases for problem [item]{dumped_problem.pretty_name()}[/item]. Sandbox probably crashed.[/error]"
        )
        return

    pretty_print_evaluation_results(
        dumped_problem, steps.evaluate(box, testcases, testcase_logs, persist_root)
    )
