from pathlib import PosixPath
import pathlib

import typer
from codefreaker.box import package
from codefreaker.box.environment import (
    get_compilation_config,
    get_file_mapping,
    get_language,
    get_mapped_commands,
    get_sandbox_params_from_config,
)
from codefreaker.box.schema import CodeItem
from codefreaker.grading.steps import (
    DigestHolder,
    GradingArtifacts,
    GradingFileInput,
    GradingFileOutput,
)
from codefreaker.grading import steps


def get_extension(code: CodeItem) -> str:
    path: pathlib.Path = PosixPath(code.path)
    return path.suffix[1:]


def find_language_name(code: CodeItem) -> str:
    if code.language is not None:
        return get_language(code.language).name
    return get_language(get_extension(code)).name


# Compile code item and return its digest in the storage.
def compile_item(code: CodeItem) -> str:
    generator_path = PosixPath(code.path)
    language = find_language_name(code)
    compilation_options = get_compilation_config(language)
    file_mapping = get_file_mapping(language)
    dependency_cache = package.get_dependency_cache()
    sandbox = package.get_singleton_sandbox()
    sandbox_params = get_sandbox_params_from_config(compilation_options.sandbox)

    if not compilation_options.commands:
        # Language is not compiled.
        return sandbox.file_cacher.put_file_from_path(generator_path)

    # Compile the generator
    commands = get_mapped_commands(compilation_options.commands, file_mapping)

    compiled_digest = DigestHolder()

    artifacts = GradingArtifacts()
    artifacts.inputs.append(steps.testlib_grading_input())
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

    with dependency_cache(commands, [artifacts]) as is_cached:
        if not is_cached:
            if not steps.compile(
                commands=commands,
                params=sandbox_params,
                artifacts=artifacts,
                sandbox=sandbox,
            ):
                raise typer.Exit(1)

    return compiled_digest.value
