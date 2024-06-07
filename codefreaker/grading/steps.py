import dataclasses
import json
import pathlib
import shlex
from typing import List, Optional

from rich.highlighter import JSONHighlighter

from codefreaker import utils
from codefreaker.console import console
from codefreaker.config import Artifact, Language, format_vars
from codefreaker.grading.judge import sandbox
from codefreaker.grading.judge.storage import copyfileobj
from codefreaker.schema import DumpedProblem


@dataclasses.dataclass
class TestcaseIO:
    input: Optional[pathlib.Path] = None
    output: Optional[pathlib.Path] = None


@dataclasses.dataclass
class PreprocessLog:
    cmd: List[str]
    exitcode: int
    log: str


def preprocess(
    problem: DumpedProblem,
    lang: Language,
    sandbox: sandbox.SandboxBase,
    root: pathlib.Path = pathlib.Path("."),
) -> bool:
    file = root / lang.get_file(problem.code)
    submit_file = root / lang.get_submit_file(problem.code)

    if not file.is_file():
        console.print(f"[error]File {file} does not exist.[/error]")
        return False

    sandbox.create_file_from_string(file.relative_to(root), file.read_text())

    commands = lang.preprocess or []
    if not commands:
        # Code does not need preprocessing of any kind.
        return True

    logs: List[PreprocessLog] = []

    for i, command in enumerate(commands):
        formatted_command = format_vars(
            command,
            **problem.get_vars(),
            file=str(file.relative_to(root)),
            submit_file=str(submit_file.relative_to(root)),
        )
        cmd = shlex.split(formatted_command)
        stderr_file = f"preprocess-{i}.stderr"
        sandbox.params.set_stdall(stderr=stderr_file)

        if not sandbox.execute_without_std(cmd, wait=True):
            console.print(
                f"[error]Sandbox crashed while processing command {command}.[/error]",
                highlight=True,
            )
            return False

        log = PreprocessLog(
            cmd=cmd,
            exitcode=sandbox.get_exit_code(),
            log=(
                sandbox.get_file_to_string(stderr_file, maxlen=None)
                if sandbox.file_exists(stderr_file)
                else ""
            ),
        )
        logs.append(log)

        if log.exitcode != 0:
            break

    if logs and logs[-1].exitcode != 0:
        console.print(
            "Preprocessing [error]failed[/error] with command",
            utils.highligh_json_obj(logs[-1].cmd),
        )
        console.print(f"Exit code: [error]{logs[-1].exitcode}[/error]")
        console.print()
        print(logs[-1].log)
        return False

    if lang.has_submit_file():
        if not sandbox.file_exists(submit_file.relative_to(root)):
            console.print(
                f"[error]Submit file [item]{submit_file}[/item] does not exist after preprocessing.[/error]"
            )
            return False
        submit_file.write_text(
            sandbox.get_file_to_string(submit_file.relative_to(root), maxlen=None)
        )

    for artifact_name, artifact_cfg in lang.artifacts.items():
        if artifact_cfg is None:
            artifact_cfg = Artifact()
        artifact_path = format_vars(
            artifact_name,
            **problem.get_vars(),
            file=str(file.relative_to(root)),
            submit_file=str(submit_file.relative_to(root)),
        )
        if not sandbox.file_exists(artifact_path) and not artifact_cfg.optional:
            console.print(
                f"[error]Artifact {artifact_path} does not exist after preprocessing.[/error]"
            )
            return False
        artifact_dest_path = root / (artifact_cfg.filename or artifact_path)
        copyfileobj(
            sandbox.get_file(artifact_path),
            artifact_dest_path.open("wb"),
        )
        if artifact_cfg.executable:
            artifact_dest_path.chmod(0o755)

    return True
