import pathlib
import shlex
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

from codefreaker.box import package
from codefreaker.box.code import compile_item, run_item
from codefreaker.box.schema import CodeItem, Primitive
from codefreaker.box.testcases import find_built_testcase_inputs
from codefreaker.grading.steps import (
    DigestHolder,
    DigestOrDest,
    DigestOrSource,
    GradingFileOutput,
)
from codefreaker.utils import StatusProgress

HitBounds = Dict[str, Tuple[bool, bool]]


class TestcaseValidationInfo(BaseModel):
    group: str
    path: pathlib.Path
    ok: bool
    hit_bounds: HitBounds
    message: Optional[str] = None


def _compile_validator(validator: CodeItem) -> str:
    return compile_item(validator)


def _bounds_or(lhs: Tuple[bool, bool], rhs: Tuple[bool, bool]) -> Tuple[bool, bool]:
    return (lhs[0] or rhs[0], lhs[1] or rhs[1])


def _process_bounds(log: str) -> HitBounds:
    bounds: HitBounds = {}
    for line in log.splitlines():
        k, v = line.split(':')
        k = k[1:-1]
        v = v.strip()

        hit = ('min-value-hit' in v, 'max-value-hit' in v)
        if k not in bounds:
            bounds[k] = hit
            continue
        bounds[k] = _bounds_or(bounds[k], hit)
    return bounds


def _validate_testcase(
    testcase: pathlib.Path,
    validator: CodeItem,
    validator_digest: str,
    vars: Optional[Dict[str, Primitive]] = None,
) -> Tuple[bool, Optional[str], HitBounds]:
    vars = vars or {}
    for var in vars:
        assert (
            var.isidentifier()
        ), f'Variable {var} should be a valid Python identifier.'
    # TODO: check if needs to do some escaping
    var_args = [f'--{k}={v}' for k, v in vars.items()]
    var_args.extend(['--testOverviewLogFileName', 'validator.log'])

    message_digest = DigestHolder()
    log_digest = DigestHolder()
    run_log = run_item(
        validator,
        DigestOrSource.create(validator_digest),
        stdin=DigestOrSource.create(testcase),
        stderr=DigestOrDest.create(message_digest),
        outputs=[
            GradingFileOutput(
                src=pathlib.Path('validator.log'),
                digest=log_digest,
                optional=True,
            )
        ],
        extra_args=shlex.join(var_args) if var_args else None,
    )
    log_overview = ''
    if log_digest.value is not None:
        log_overview = package.get_digest_as_string(log_digest.value or '')
    message = package.get_digest_as_string(message_digest.value or '')
    return (
        run_log is not None and run_log.exitcode == 0,
        message,
        _process_bounds(log_overview or ''),
    )


def compile_validators(
    progress: Optional[StatusProgress] = None,
) -> Dict[str, str]:
    pkg = package.find_problem_package_or_die()

    group_to_compiled_digest = {}

    for group in pkg.testcases:
        validator = group.validator or pkg.validator
        if validator is None:
            continue
        if progress:
            progress.update(
                f'Compiling validator for group [item]{group.name}[/item]...'
            )
        group_to_compiled_digest[group.name] = _compile_validator(validator)

    return group_to_compiled_digest


def validate_testcases(
    progress: Optional[StatusProgress] = None,
) -> List[TestcaseValidationInfo]:
    def step():
        if progress is not None:
            progress.step()

    pkg = package.find_problem_package_or_die()

    group_to_compiled_digest = compile_validators(progress)

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
            ok, message, hit_bounds = _validate_testcase(
                testcase, validator, compiled_digest, vars=pkg.vars
            )
            validation_info.append(
                TestcaseValidationInfo(
                    group=group.name,
                    path=testcase,
                    ok=ok,
                    hit_bounds=hit_bounds,
                    message=message,
                )
            )
            step()

    return validation_info
