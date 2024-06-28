import pathlib
import shlex
import shutil
from pathlib import PosixPath
from typing import Dict, List, Optional, Set

import typer

from robox import console
from robox.box import package
from robox.box.code import compile_item, run_item
from robox.box.environment import (
    EnvironmentSandbox,
    ExecutionConfig,
)
from robox.box.schema import CodeItem, Generator, Testcase
from robox.box.testcases import find_built_testcases
from robox.grading.steps import (
    DigestHolder,
    DigestOrDest,
    DigestOrSource,
)
from robox.utils import StatusProgress


def _compile_generator(generator: CodeItem) -> str:
    return compile_item(generator)


def _get_group_input(group_path: pathlib.Path, i: int) -> pathlib.Path:
    return group_path / f'{i:03d}.in'


def _get_group_output(group_path: pathlib.Path, i: int) -> pathlib.Path:
    return group_path / f'{i:03d}.out'


def _copy_testcase_over(testcase: Testcase, group_path: pathlib.Path, i: int):
    shutil.copy(
        str(testcase.inputPath),
        _get_group_input(group_path, i),
    )
    if testcase.outputPath is not None and testcase.outputPath.is_file():
        shutil.copy(
            str(testcase.outputPath),
            _get_group_output(group_path, i),
        )


def _run_generator(
    generator: Generator,
    args: Optional[str],
    compiled_digest: str,
    group_path: pathlib.Path,
    i: int = 0,
):
    run_log = run_item(
        generator,
        DigestOrSource.create(compiled_digest),
        stdout=DigestOrDest.create(_get_group_input(group_path, i)),
        extra_args=args or None,
    )

    if not run_log or run_log.exitcode != 0:
        console.console.print(
            f'Failed generating test {i} from group path {group_path}',
            style='error',
        )
        raise typer.Exit(1)


def get_all_built_testcases() -> Dict[str, List[Testcase]]:
    pkg = package.find_problem_package_or_die()
    res = {group.name: find_built_testcases(group) for group in pkg.testcases}
    return res


def generate_outputs_for_testcases(progress: Optional[StatusProgress] = None):
    def step():
        if progress is not None:
            progress.step()

    pkg = package.find_problem_package_or_die()

    built_testcases = get_all_built_testcases()
    main_solution = package.get_main_solution()
    solution_digest: Optional[str] = None

    if main_solution is not None:
        if progress:
            progress.update('Compiling main solution...')
        solution_digest = compile_item(main_solution)

    sandbox = EnvironmentSandbox()
    sandbox.timeLimit = pkg.timeLimit * 2
    sandbox.wallTimeLimit = pkg.timeLimit * 2
    sandbox.memoryLimit = pkg.memoryLimit
    extra_config = ExecutionConfig(sandbox=sandbox)

    for group in pkg.testcases:
        group_testcases = built_testcases[group.name]

        for testcase in group_testcases:
            input_path = testcase.inputPath
            output_path = testcase.outputPath

            assert output_path is not None
            if output_path.is_file():
                continue
            if main_solution is None or solution_digest is None:
                console.console.print(
                    'No main solution found to generate outputs for testcases',
                    style='error',
                )
                raise typer.Exit(1)

            run_log = run_item(
                main_solution,
                DigestOrSource.create(solution_digest),
                stdin=DigestOrSource.create(input_path),
                stdout=DigestOrDest.create(output_path),
                extra_config=extra_config,
            )

            if run_log is None or run_log.exitcode != 0:
                console.console.print(
                    f'Failed generating output for {input_path}',
                    style='error',
                )
                if run_log is not None:
                    console.console.print(
                        f'Program exited with code {run_log.exitcode}',
                        style='error',
                    )
                raise typer.Exit(1)

            step()


def compile_generators(
    progress: Optional[StatusProgress] = None,
    tracked_generators: Optional[Set[str]] = None,
) -> Dict[str, str]:
    def update_status(text: str):
        if progress is not None:
            progress.update(text)

    pkg = package.find_problem_package_or_die()

    generator_to_compiled_digest = {}

    for generator in pkg.generators:
        if tracked_generators is not None and generator.name not in tracked_generators:
            continue
        update_status(f'Compiling generator [item]{generator.name}[/item]')
        generator_to_compiled_digest[generator.name] = _compile_generator(generator)

    return generator_to_compiled_digest


def generate_testcases(progress: Optional[StatusProgress] = None):
    def step():
        if progress is not None:
            progress.step()

    pkg = package.find_problem_package_or_die()
    cacher = package.get_file_cacher()

    compiled_generators = compile_generators(progress=progress)

    for testcase in pkg.testcases:
        group_path = package.get_build_testgroup_path(testcase.name)

        i = 0
        # Individual testcases.
        for tc in testcase.testcases or []:
            _copy_testcase_over(tc, group_path, i)
            i += 1
            step()

        # Glob testcases.
        if testcase.testcaseGlob:
            matched_inputs = sorted(PosixPath().glob(testcase.testcaseGlob))

            for input_path in matched_inputs:
                if not input_path.is_file() or input_path.suffix != '.in':
                    continue
                output_path = input_path.parent / f'{input_path.stem}.out'
                tc = Testcase(inputPath=input_path, outputPath=output_path)
                _copy_testcase_over(tc, group_path, i)
                i += 1
                step()

        # Run single generators.
        for generator_call in testcase.generators:
            generator = package.get_generator(generator_call.name)
            if generator.name not in compiled_generators:
                console.console.print(f'Generator {generator.name} not compiled')
                raise typer.Exit(1)

            _run_generator(
                generator,
                generator_call.args,
                compiled_generators[generator.name],
                group_path,
                i,
            )
            i += 1
            step()

        # Run generator script.
        if testcase.generatorScript is not None:
            script_digest = DigestHolder()
            if testcase.generatorScript.path.suffix == '.txt':
                script_digest.value = cacher.put_file_from_path(
                    testcase.generatorScript.path
                )
            else:
                compiled_digest = compile_item(testcase.generatorScript)

                run_log = run_item(
                    testcase.generatorScript,
                    DigestOrSource.create(compiled_digest),
                    stdout=DigestOrDest.create(script_digest),
                )

                if run_log is None or run_log.exitcode != 0:
                    console.console.print(
                        f'Could not run generator script for group {testcase.name}'
                    )
                    raise typer.Exit(1)

            assert script_digest.value
            script = cacher.get_file_content(script_digest.value).decode()
            lines = script.splitlines()

            # Run each line from generator script.
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                generator_name = shlex.split(line)[0]
                generator = package.get_generator(generator_name)
                if generator.name not in compiled_generators:
                    console.console.print(f'Generator {generator.name} not compiled')
                    raise typer.Exit(1)

                _run_generator(
                    generator,
                    shlex.join(shlex.split(line)[1:]),
                    compiled_generators[generator.name],
                    group_path,
                    i,
                )
                i += 1
                step()
