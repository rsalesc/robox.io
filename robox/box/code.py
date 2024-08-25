import pathlib
import shlex
import sys
from pathlib import PosixPath
from typing import List, Optional

import typer
from pydantic import BaseModel

from robox.box import download, package
from robox.box.environment import (
    ExecutionConfig,
    get_compilation_config,
    get_execution_config,
    get_extension_or_default,
    get_file_mapping,
    get_language,
    get_mapped_command,
    get_mapped_commands,
    get_sandbox_params_from_config,
    merge_execution_configs,
)
from robox.box.schema import CodeItem
from robox.grading import steps
from robox.grading.steps import (
    DigestHolder,
    DigestOrDest,
    DigestOrSource,
    GradingArtifacts,
    GradingFileInput,
    GradingFileOutput,
    GradingLogsHolder,
    RunLog,
)


class MacExtension(BaseModel):
    gpp_alternative: Optional[str] = None


def normalize_for_macos(commands: List[str]) -> List[str]:
    def normalize(command: str) -> str:
        extension = get_extension_or_default('mac', MacExtension)
        if extension.gpp_alternative is None:
            return command
        return command.replace('g++', extension.gpp_alternative)

    return [normalize(command) for command in commands]


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
    if sys.platform == 'darwin':
        commands = normalize_for_macos(commands)

    compiled_digest = DigestHolder()

    artifacts = GradingArtifacts()
    artifacts.inputs.extend(
        GradingFileInput(src=src, dest=dest)
        for src, dest in package.get_compilation_files(code)
    )
    download.maybe_add_testlib(code, artifacts)
    download.maybe_add_jngen(code, artifacts)
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

    with dependency_cache(
        commands, [artifacts], sandbox_params.get_cacheable_params()
    ) as is_cached:
        if not is_cached and not steps.compile(
            commands=commands,
            params=sandbox_params,
            artifacts=artifacts,
            sandbox=sandbox,
        ):
            raise typer.Exit(1)

    assert compiled_digest.value is not None
    return compiled_digest.value


def run_item(
    code: CodeItem,
    executable: DigestOrSource,
    stdin: Optional[DigestOrSource] = None,
    stdout: Optional[DigestOrDest] = None,
    stderr: Optional[DigestOrDest] = None,
    inputs: Optional[List[GradingFileInput]] = None,
    outputs: Optional[List[GradingFileOutput]] = None,
    extra_args: Optional[str] = None,
    extra_config: Optional[ExecutionConfig] = None,
) -> Optional[RunLog]:
    language = find_language_name(code)
    execution_options = get_execution_config(language)
    if extra_config is not None:
        execution_options = merge_execution_configs([execution_options, extra_config])
    file_mapping = get_file_mapping(language)
    dependency_cache = package.get_dependency_cache()
    sandbox = package.get_singleton_sandbox()
    sandbox_params = get_sandbox_params_from_config(execution_options.sandbox)

    sandbox_params.set_stdall(
        stdin=PosixPath(file_mapping.input) if stdin is not None else None,
        stdout=PosixPath(file_mapping.output) if stdout is not None else None,
        stderr=PosixPath(file_mapping.error) if stderr is not None else None,
    )

    assert execution_options.command
    command = get_mapped_command(execution_options.command, file_mapping)

    if extra_args is not None:
        splitted_command = shlex.split(command)
        splitted_command.extend(shlex.split(extra_args))
        command = shlex.join(splitted_command)

    artifacts = GradingArtifacts()
    artifacts.logs = GradingLogsHolder()
    artifacts.inputs.append(
        GradingFileInput(
            **executable.expand(),
            dest=PosixPath(file_mapping.executable),
            executable=True,
        )
    )
    if stdin is not None:
        artifacts.inputs.append(
            GradingFileInput(
                **stdin.expand(),
                dest=PosixPath(file_mapping.input),
            )
        )
    if stdout is not None:
        artifacts.outputs.append(
            GradingFileOutput(
                src=PosixPath(file_mapping.output),
                **stdout.expand(),
            )
        )
    if stderr is not None:
        artifacts.outputs.append(
            GradingFileOutput(
                src=PosixPath(file_mapping.error),
                **stderr.expand(),
            )
        )
    if inputs:
        artifacts.inputs.extend(inputs)
    if outputs:
        artifacts.outputs.extend(outputs)

    with dependency_cache(
        [command], [artifacts], sandbox_params.get_cacheable_params()
    ) as is_cached:
        if not is_cached:
            steps.run(
                command=command,
                params=sandbox_params,
                artifacts=artifacts,
                sandbox=sandbox,
            )

    return artifacts.logs.run
