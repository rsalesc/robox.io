import collections
from typing import Dict, List
from codefreaker.box import checkers
from codefreaker.box.testcases import find_built_testcases
from codefreaker.box.environment import EnvironmentSandbox, ExecutionConfig
from codefreaker.box.schema import Solution, Testcase, TestcaseGroup
from codefreaker.box.code import compile_item, run_item
from codefreaker.box import package
from codefreaker.grading.steps import (
    CheckerResult,
    DigestOrDest,
    DigestOrSource,
    RunLog,
)


def compile_solutions():
    pkg = package.find_problem_package_or_die()

    compiled_solutions = {}

    for solution in pkg.solutions:
        compiled_solutions[solution.path] = compile_item(solution)

    return compiled_solutions


def run_solution(
    solution: Solution, compiled_digest: str, checker_digest: str, index: int
) -> Dict[str, List[CheckerResult]]:
    pkg = package.find_problem_package_or_die()

    sandbox = EnvironmentSandbox()
    sandbox.timeLimit = pkg.timeLimit * 2
    sandbox.wallTimeLimit = pkg.timeLimit * 2
    sandbox.memoryLimit = pkg.memoryLimit
    extra_config = ExecutionConfig(sandbox=sandbox)

    res = collections.defaultdict(list)

    for group in pkg.testcases:
        testcases = find_built_testcases(group)
        for testcase in testcases:
            runs_dir = package.get_problem_runs_dir()
            output_path = runs_dir / f"{index}" / group.name / testcase.outputPath.name
            error_path = (
                runs_dir
                / f"{index}"
                / group.name
                / testcase.outputPath.with_suffix(".err").name
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            run_log = run_item(
                solution,
                DigestOrSource.create(compiled_digest),
                stdin=DigestOrSource.create(testcase.inputPath),
                stdout=DigestOrDest.create(output_path),
                stderr=DigestOrDest.create(error_path),
                extra_config=extra_config,
            )

            checker_result = checkers.check(
                checker_digest,
                run_log,
                testcase,
                program_output=output_path,
            )
            res[group.name].append(checker_result)

    return dict(res)


def run_solutions() -> List[Dict[str, List[CheckerResult]]]:
    pkg = package.find_problem_package_or_die()

    checker_digest = checkers.compile_checker()
    compiled_solutions = compile_solutions()
    res = []

    for i, solution in enumerate(pkg.solutions):
        results_per_group = run_solution(
            solution, compiled_solutions[solution.path], checker_digest, i
        )
        res.append(results_per_group)

    return res
