from pathlib import PosixPath
import pathlib
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel
import typer
from codefreaker.box.testcases import find_built_testcase_inputs
from codefreaker.box.environment import (
    get_compilation_config,
    get_execution_config,
    get_file_mapping,
    get_mapped_command,
    get_mapped_commands,
    get_sandbox_params_from_config,
)
from codefreaker.box.code import compile_item, find_language_name, run_item
from codefreaker.box.schema import CodeItem
from codefreaker.box import package
from codefreaker.grading.steps import (
    DigestHolder,
    DigestOrDest,
    DigestOrSource,
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
    message: Optional[str] = None


def _compile_validator(validator: CodeItem) -> str:
    return compile_item(validator)


def _validate_testcase(
    testcase: pathlib.Path, validator: CodeItem, validator_digest: str
) -> Tuple[bool, Optional[str]]:
    message_digest = DigestHolder()
    run_log = run_item(
        validator,
        DigestOrSource.create(validator_digest),
        stdin=DigestOrSource.create(testcase),
        stderr=DigestOrDest.create(message_digest),
    )
    message = package.get_digest_as_string(message_digest.value or '')
    return (run_log is not None and run_log.exitcode == 0, message)


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

        testcases = find_built_testcase_inputs(group)

        for testcase in testcases:
            ok, message = _validate_testcase(testcase, validator, compiled_digest)
            validation_info.append(
                TestcaseValidationInfo(
                    group=group.name,
                    path=testcase,
                    ok=ok,
                    message=message,
                )
            )

    return validation_info
