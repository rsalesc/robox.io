import pathlib
from pathlib import PosixPath
from typing import List

from rbx import config
from rbx.config import Artifact, Language, format_vars
from rbx.grading import steps
from rbx.grading.judge.sandbox import MERGE_STDERR, SandboxParams
from rbx.grading.steps import (
    GradingArtifacts,
    GradingFileInput,
    GradingFileOutput,
    TestcaseIO,
)
from rbx.schema import DumpedProblem, Problem


def build_formatted_command(
    command: str, problem: DumpedProblem, lang: Language
) -> str:
    return format_vars(
        command,
        **problem.get_vars(),
        file=lang.get_file(problem.code),
        submit_file=lang.get_submit_file(problem.code),
    )


def build_preprocess_commands(problem: DumpedProblem, lang: Language) -> List[str]:
    return [
        build_formatted_command(cmd, problem, lang) for cmd in (lang.preprocess or [])
    ]


def build_preprocess_sandbox_params() -> SandboxParams:
    params = SandboxParams(
        max_processes=None,
        preserve_env=True,
    )
    params.add_mapped_directory(pathlib.Path('/usr'))
    params.add_mapped_directory(pathlib.Path('/etc'))
    return params


def build_compile_grading_artifacts(
    problem: DumpedProblem, lang: Language
) -> GradingArtifacts:
    res = GradingArtifacts(root=PosixPath('.'))
    file = lang.get_file(problem.code)
    submit_file = lang.get_submit_file(problem.code)
    # Copy input file.
    res.inputs.append(GradingFileInput(src=PosixPath(file), dest=PosixPath(file)))
    # Copy output file.
    if lang.has_submit_file():
        res.outputs.append(
            GradingFileOutput(
                src=PosixPath(submit_file),
                dest=PosixPath(submit_file),
            )
        )
    # Copy other artifacts.
    for artifact_name, artifact_cfg in lang.artifacts.items():
        artifact_cfg = artifact_cfg or Artifact()
        artifact_path = format_vars(
            artifact_name, **problem.get_vars(), file=file, submit_file=submit_file
        )
        res.outputs.append(
            GradingFileOutput(
                src=PosixPath(artifact_path),
                dest=PosixPath(artifact_cfg.filename or artifact_path),
                optional=artifact_cfg.optional,
                executable=artifact_cfg.executable,
            )
        )

    return res


def build_run_sandbox_params(problem: Problem, has_input: bool) -> SandboxParams:
    params = SandboxParams()
    params.timeout = problem.timeLimit * 2
    params.wallclock_timeout = problem.timeLimit * 5
    params.address_space = problem.memoryLimit or 1024  # 1 GB
    params.set_stdall(
        stdin=PosixPath('stdin.txt') if has_input else None,
        stdout=PosixPath('stdout.txt'),
        stderr=MERGE_STDERR,
    )
    return params


def build_run_grading_artifacts(
    testcase: TestcaseIO, persist_root: pathlib.Path
) -> GradingArtifacts:
    res = GradingArtifacts(root=PosixPath('.'))
    res.inputs.append(
        GradingFileInput(
            src=testcase.input,
            dest=PosixPath('stdin.txt'),
        )
    )
    res.outputs.append(
        GradingFileOutput(
            src=PosixPath('stdout.txt'),
            dest=persist_root / f'stdout-{testcase.index}.txt',
            maxlen=steps.MAX_STDOUT_LEN,
        )
    )
    return res


def build_checker_compile_grading_artifacts(
    problem: DumpedProblem, persist_root: pathlib.Path
) -> GradingArtifacts:
    res = GradingArtifacts(root=PosixPath('.'))
    if not problem.checker:
        return res

    checker_path = PosixPath(problem.checker)
    if not checker_path.is_file():
        checker_path = config.get_builtin_checker(problem.checker)
    if not checker_path:
        return res

    res.inputs.append(GradingFileInput(src=checker_path, dest=PosixPath('checker.cpp')))
    testlib = config.get_testlib()
    if testlib.is_file():
        res.inputs.append(GradingFileInput(src=testlib, dest=PosixPath('testlib.h')))
    res.outputs.append(
        GradingFileOutput(
            src=PosixPath('checker'), dest=persist_root / 'checker', executable=True
        )
    )
    return res


def build_checker_run_grading_artifacts(
    problem: DumpedProblem, persist_root: pathlib.Path
) -> GradingArtifacts:
    res = GradingArtifacts(root=PosixPath('.'))
    if not problem.checker:
        return res
    res.inputs.append(
        GradingFileInput(
            src=persist_root / 'checker', dest=PosixPath('checker'), executable=True
        )
    )
    return res
