from pathlib import PosixPath
import shlex
from typing import Dict

import typer
from codefreaker.box import package
from codefreaker.box.code import find_language_name
from codefreaker.box.environment import (
    get_compilation_config,
    get_execution_config,
    get_file_mapping,
    get_mapped_command,
    get_mapped_commands,
    get_sandbox_params_from_config,
)
from codefreaker.box.schema import CodeItem, Generator, GeneratorCall
from codefreaker.grading import steps
from codefreaker.grading.steps import (
    DigestHolder,
    GradingArtifacts,
    GradingFileInput,
    GradingFileOutput,
)
from codefreaker import console


def _compile_generator(generator: CodeItem) -> str:
    generator_path = PosixPath(generator.path)
    language = find_language_name(generator)
    compilation_options = get_compilation_config(language)
    file_mapping = get_file_mapping(language)
    dependency_cache = package.get_dependency_cache()
    sandbox = package.get_singleton_sandbox()
    sandbox_params = get_sandbox_params_from_config(compilation_options.sandbox)

    # Compile the generator
    commands = get_mapped_commands(compilation_options.commands, file_mapping)

    compiled_digest = DigestHolder()

    artifacts = GradingArtifacts()
    artifacts.inputs.append(
        GradingFileInput(src=generator_path, dest=PosixPath(file_mapping.compilable))
    )
    artifacts.outputs.append(
        GradingFileOutput(
            src=PosixPath(file_mapping.executable),
            digest=compiled_digest,
            executable=True,
        )
    )

    with dependency_cache(commands, [artifacts]):
        steps.compile(
            commands=commands,
            params=sandbox_params,
            artifacts=artifacts,
            sandbox=sandbox,
        )

    return compiled_digest.value


def _run_generator(
    generator: Generator,
    args: str,
    compiled_digest: str,
    group_path: PosixPath,
    i: int = 0,
):
    language = find_language_name(generator)
    execution_options = get_execution_config(language)
    file_mapping = get_file_mapping(language)
    dependency_cache = package.get_dependency_cache()
    sandbox = package.get_singleton_sandbox()
    sandbox_params = get_sandbox_params_from_config(execution_options.sandbox)

    sandbox_params.set_stdio(stdout=file_mapping.output)

    command = get_mapped_command(execution_options.command, file_mapping)
    splitted_command = shlex.split(command)
    # Add custom generator args.
    if args:
        splitted_command.extend(shlex.split(args))

    command = shlex.join(splitted_command)

    artifacts = GradingArtifacts()
    artifacts.inputs.append(
        GradingFileInput(
            digest=DigestHolder(value=compiled_digest),
            dest=PosixPath(file_mapping.executable),
            executable=True,
        )
    )
    output_fn = f"{i:03d}.in"
    artifacts.outputs.append(
        GradingFileOutput(
            src=PosixPath(file_mapping.output),
            dest=group_path / output_fn,
        )
    )

    with dependency_cache([command], [artifacts]):
        steps.run(command, sandbox_params, sandbox, artifacts)


def compile_generators() -> Dict[str, str]:
    pkg = package.find_problem_package_or_die()

    generator_to_compiled_digest = {}

    for generator in pkg.generators:
        generator_to_compiled_digest[generator.name] = _compile_generator(generator)

    return generator_to_compiled_digest


def generate_testcases():
    pkg = package.find_problem_package_or_die()

    compiled_generators = compile_generators()

    for testcase in pkg.testcases:
        group_path = package.get_build_testgroup_path(testcase.name)

        i = 0

        # Run single generators.
        for generator_call in testcase.generators:
            generator = package.get_generator(generator_call.name)
            if generator.name not in compiled_generators:
                console.console.print(f"Generator {generator.name} not compiled")
                raise typer.Exit(1)

            _run_generator(
                generator,
                generator_call.args,
                compiled_generators[generator.name],
                group_path,
                i,
            )
            i += 1
