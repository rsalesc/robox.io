from pathlib import PosixPath
import pathlib
from typing import Dict, List

from pydantic import BaseModel
import typer
from codefreaker.box.testcases import find_testcases
from codefreaker.box.environment import (
    get_compilation_config,
    get_execution_config,
    get_file_mapping,
    get_mapped_command,
    get_mapped_commands,
    get_sandbox_params_from_config,
)
from codefreaker.box.code import find_language_name
from codefreaker.box.schema import CodeItem
from codefreaker.box import package
from codefreaker.grading.steps import (
    DigestHolder,
    GradingArtifacts,
    GradingFileInput,
    GradingFileOutput,
    GradingLogsHolder,
)
from codefreaker.grading import steps
from codefreaker import console


class TestcaseValidationInfo(BaseModel):
    group: str
    path: pathlib.Path
    ok: bool


def _compile_validator(validator: CodeItem) -> str:
    validator_path = PosixPath(validator.path)
    language = find_language_name(validator)
    compilation_options = get_compilation_config(language)
    file_mapping = get_file_mapping(language)
    dependency_cache = package.get_dependency_cache()
    sandbox = package.get_singleton_sandbox()
    sandbox_params = get_sandbox_params_from_config(compilation_options.sandbox)

    # Compile the validator
    commands = get_mapped_commands(compilation_options.commands, file_mapping)

    compiled_digest = DigestHolder()

    artifacts = GradingArtifacts()
    artifacts.inputs.append(steps.testlib_grading_input())
    artifacts.inputs.append(
        GradingFileInput(src=validator_path, dest=PosixPath(file_mapping.compilable))
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


def _validate_testcase(
    testcase: pathlib.Path, validator: CodeItem, validator_digest: str
) -> bool:
    language = find_language_name(validator)
    execution_options = get_execution_config(language)
    file_mapping = get_file_mapping(language)
    dependency_cache = package.get_dependency_cache()
    sandbox = package.get_singleton_sandbox()
    sandbox_params = get_sandbox_params_from_config(execution_options.sandbox)

    sandbox_params.set_stdall(stdin=file_mapping.input, stderr=file_mapping.output)

    command = get_mapped_command(execution_options.command, file_mapping)
    validator_output = DigestHolder()
    logs = GradingLogsHolder()

    artifacts = GradingArtifacts()
    artifacts.logs = logs
    artifacts.inputs.append(
        GradingFileInput(
            digest=DigestHolder(value=validator_digest),
            dest=PosixPath(file_mapping.executable),
            executable=True,
        )
    )
    artifacts.inputs.append(
        GradingFileInput(
            src=testcase,
            dest=PosixPath(file_mapping.input),
        )
    )
    artifacts.outputs.append(
        GradingFileOutput(
            src=PosixPath(file_mapping.output),
            digest=validator_output,
        )
    )

    with dependency_cache([command], [artifacts]) as is_cached:
        if not is_cached:
            steps.run(
                command=command,
                params=sandbox_params,
                artifacts=artifacts,
                sandbox=sandbox,
            )

    return logs.run is not None and logs.run.exitcode == 0


def compile_validators() -> Dict[str, str]:
    pkg = package.find_problem_package_or_die()

    group_to_compiled_digest = {}

    for group in pkg.testcases:
        validator = group.validator or pkg.validator
        if validator is None:
            continue
        group_to_compiled_digest[group.name] = _compile_validator(validator)

    return group_to_compiled_digest


def validate_testcases() -> List[TestcaseValidationInfo]:
    pkg = package.find_problem_package_or_die()

    group_to_compiled_digest = compile_validators()

    validation_info = []

    for group in pkg.testcases:
        validator = group.validator or pkg.validator
        if validator is None:
            continue
        if group.name not in group_to_compiled_digest:
            continue
        compiled_digest = group_to_compiled_digest[group.name]

        testcases = find_testcases(group)

        for testcase in testcases:
            validation_info.append(
                TestcaseValidationInfo(
                    group=group.name,
                    path=testcase,
                    ok=_validate_testcase(testcase, validator, compiled_digest),
                )
            )

    return validation_info
