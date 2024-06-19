from pathlib import PosixPath
from typing import Dict
from codefreaker.box import package
from codefreaker.box.code import find_language_name
from codefreaker.box.environment import (
    get_compilation_config,
    get_file_mapping,
    get_mapped_commands,
    get_sandbox_params_from_config,
)
from codefreaker.box.schema import CodeItem
from codefreaker.grading import steps
from codefreaker.grading.steps import (
    DigestHolder,
    GradingArtifacts,
    GradingFileInput,
    GradingFileOutput,
)


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


def compile_generators() -> Dict[str, str]:
    pkg = package.find_problem_package_or_die()

    generator_to_compiled_digest = {}

    for generator in pkg.generators:
        generator_to_compiled_digest[generator.name] = _compile_generator(generator)

    return generator_to_compiled_digest


def generate_testcases():
    pkg = package.find_problem_package_or_die()

    compile_generators()
