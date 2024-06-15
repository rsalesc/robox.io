from pathlib import PosixPath
import pathlib
from typing import List, Optional
from codefreaker.config import Artifact, Language, format_vars
from codefreaker.grading.judge.sandbox import SandboxParams
from codefreaker.grading.steps import (
    GradingArtifacts,
    GradingFileInput,
    GradingFileOutput,
)
from codefreaker.schema import DumpedProblem


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
    return [build_formatted_command(cmd, problem, lang) for cmd in lang.preprocess]


def build_preprocess_sandbox_params() -> SandboxParams:
    params = SandboxParams(
        max_processes=None,
        preserve_env=True,
    )
    params.add_mapped_directory(pathlib.Path("/usr"))
    params.add_mapped_directory(pathlib.Path("/etc"))
    return params


def build_grading_artifacts(problem: DumpedProblem, lang: Language) -> GradingArtifacts:
    res = GradingArtifacts(root=PosixPath("."))
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
