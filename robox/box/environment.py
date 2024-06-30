import functools
import pathlib
from typing import List, Optional, Type, TypeVar

import typer
from pydantic import BaseModel, ConfigDict

from robox import config, console, utils
from robox.grading.judge.sandbox import SandboxBase, SandboxParams
from robox.grading.judge.sandboxes.isolate import IsolateSandbox
from robox.grading.judge.sandboxes.stupid_sandbox import StupidSandbox

T = TypeVar('T', bound=BaseModel)


class FileMapping(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Path where to copy the stdin file to before running the program,
    # relative to the sandbox root.
    input: str = 'stdin'

    # Path where to output the stdout file after running the program,
    # relative to the sandbox root.
    output: str = 'stdout'

    # Path where to output the stderr file after running the program,
    # relative to the sandbox root.
    error: str = 'stderr'

    # Path where to copy the compilable file to before compiling the program,
    # relative to the sandbox root.
    compilable: str = 'compilable'

    # Path to where to output the executable file after compiling the program,
    # relative to the sandbox root.
    executable: str = 'executable'


class EnvironmentSandbox(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Max. number of process to allow to run concurrently for the program.
    maxProcesses: Optional[int] = 1

    # Time limit in milliseconds to allow the program to run.
    timeLimit: Optional[int] = None

    # Wall time limit in milliseconds to allow the program to run.
    wallTimeLimit: Optional[int] = None

    # Memory limit in MiB.
    memoryLimit: Optional[int] = None

    # Stack limit in MiB.
    stackLimit: Optional[int] = None

    # Whether to preserve env. variables coming from the host.
    preserveEnv: Optional[bool] = False

    # Directories in the host that should be read-only exposed to the sandbox.
    mirrorDirs: Optional[List[str]] = []


class CompilationConfig(BaseModel):
    # Commands to compile the program.
    commands: Optional[List[str]] = []

    # Sandbox configuration to use when compiling for this language.
    sandbox: Optional[EnvironmentSandbox] = None


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Command to run the program.
    command: Optional[str] = None

    # Sandbox configuration to use when executing for this language.
    sandbox: Optional[EnvironmentSandbox] = None


class EnvironmentLanguage(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Identifier of this language within this environment.
    name: str

    # Readable name for this language.
    readable_name: Optional[str] = None

    # File extension supported by this language. If there's only one language
    # that supports a certain file extension in the environment, the tool
    # will automatically identify the language based on such extension.
    extension: str

    # Compilation config to use when compiling programs for this language.
    compilation: Optional[CompilationConfig] = None

    # Execution config to use when running programs for this language.
    execution: ExecutionConfig

    # Mapping for files within the sandbox. If not specified, the default mapping
    # for the environment will be used.
    fileMapping: Optional[FileMapping] = None


class Environment(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Default mapping for files within the sandbox. Fields in the mapping can be
    # individually overridden in the language configuration.
    defaultFileMapping: Optional[FileMapping] = None

    # Default compilation configuration to use when compiling programs. Fields in
    # the compilation config can be individually overridden in the language configuration.
    defaultCompilation: Optional[CompilationConfig] = None

    # Default execution configuration to use when running programs. Fields in the
    # execution config can be individually overridden in the language configuration.
    defaultExecution: Optional[ExecutionConfig] = None

    # Configuration for each language supported in this environment.
    languages: List[EnvironmentLanguage] = []

    # Identifier of the sandbox used by this environment (e.g. "stupid", "isolate")
    sandbox: str = 'stupid'

    # Identifier of the preset that should be used when creating new problems.
    preset: str = 'default'


def get_environment_path(env: str) -> pathlib.Path:
    return config.get_app_file(pathlib.PosixPath('envs') / f'{env}.rbx.yml')


@functools.cache
def get_environment(env: Optional[str] = None) -> Environment:
    env_path = get_environment_path(env or config.get_config().boxEnvironment)
    if not env_path.is_file():
        console.console.print(
            f'Environment file [item]{env_path}[/item] not found.', style='error'
        )
        raise typer.Exit()
    return utils.model_from_yaml(Environment, env_path.read_text())


@functools.cache
def get_language(name: str) -> EnvironmentLanguage:
    for lang in get_environment().languages:
        if lang.name == name:
            return lang
    console.console.print(f'Language [item]{name}[/item] not found.', style='error')
    raise typer.Exit()


def _merge_shallow_models(model: Type[T], base: T, override: T) -> T:
    return model(
        **{
            **base.model_dump(exclude_unset=True),
            **override.model_dump(exclude_unset=True),
        }
    )


def merge_compilation_configs(
    compilation_configs: List[Optional[CompilationConfig]],
) -> CompilationConfig:
    merged_cfg = CompilationConfig()
    merged_cfg.sandbox = EnvironmentSandbox(
        maxProcesses=None,
        timeLimit=10000,
        wallTimeLimit=10000,
        memoryLimit=512,
        preserveEnv=True,
        mirrorDirs=['/etc', '/usr'],
    )
    for cfg in compilation_configs:
        if cfg is None:
            continue
        merged_cfg.commands = cfg.commands or merged_cfg.commands
        if cfg.sandbox is not None:
            merged_cfg.sandbox = _merge_shallow_models(
                EnvironmentSandbox, merged_cfg.sandbox, cfg.sandbox
            )
    return merged_cfg


@functools.cache
def get_compilation_config(language: str) -> CompilationConfig:
    environment = get_environment()
    return merge_compilation_configs(
        [environment.defaultCompilation, get_language(language).compilation]
    )


def merge_execution_configs(
    execution_configs: List[Optional[ExecutionConfig]],
) -> ExecutionConfig:
    merged_cfg = ExecutionConfig()
    merged_cfg.sandbox = EnvironmentSandbox()
    for cfg in execution_configs:
        if cfg is None:
            continue
        merged_cfg.command = cfg.command or merged_cfg.command
        if cfg.sandbox is not None:
            merged_cfg.sandbox = _merge_shallow_models(
                EnvironmentSandbox, merged_cfg.sandbox, cfg.sandbox
            )
    return merged_cfg


@functools.cache
def get_execution_config(language: str) -> ExecutionConfig:
    environment = get_environment()
    return merge_execution_configs(
        [environment.defaultExecution, get_language(language).execution]
    )


@functools.cache
def get_file_mapping(language: str) -> FileMapping:
    environment = get_environment()
    return _merge_shallow_models(
        FileMapping,
        environment.defaultFileMapping or FileMapping(),
        get_language(language).fileMapping or FileMapping(),
    )


@functools.cache
def get_sandbox_type() -> Type[SandboxBase]:
    used_sandbox = get_environment().sandbox
    if used_sandbox == 'stupid':
        return StupidSandbox
    if used_sandbox == 'isolate':
        return IsolateSandbox
    return StupidSandbox


def get_mapped_commands(
    commands: List[str], mapping: Optional[FileMapping] = None
) -> List[str]:
    mapping = mapping or FileMapping()
    return [cmd.format(**mapping.model_dump()) for cmd in commands]


def get_mapped_command(command: str, mapping: Optional[FileMapping] = None) -> str:
    return get_mapped_commands([command], mapping)[0]


def get_sandbox_params_from_config(
    config: Optional[EnvironmentSandbox],
) -> SandboxParams:
    config = config or EnvironmentSandbox()
    params = SandboxParams()
    params.timeout = config.timeLimit
    params.wallclock_timeout = config.wallTimeLimit
    params.address_space = config.memoryLimit
    params.max_processes = config.maxProcesses
    if config.preserveEnv:
        params.preserve_env = True
    if config.mirrorDirs:
        for dir in config.mirrorDirs:
            path = pathlib.Path(dir)
            params.add_mapped_directory(path)
    return params
