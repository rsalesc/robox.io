from typing import List, Optional
from pydantic import BaseModel


class FileMapping(BaseModel):
    # Path where to copy the stdin file to before running the program,
    # relative to the sandbox root.
    input: Optional[str] = "stdin"

    # Path where to output the stdout file after running the program,
    # relative to the sandbox root.
    output: Optional[str] = "stdout"

    # Path where to copy the compilable file to before compiling the program,
    # relative to the sandbox root.
    compilable: Optional[str] = "compilable"

    # Path to where to output the executable file after compiling the program,
    # relative to the sandbox root.
    executable: Optional[str] = "executable"


class EnvironmentSandbox(BaseModel):
    # Max. number of process to allow to run concurrently for the program.
    maxProcesses: Optional[int] = 1

    # Time limit in milliseconds to allow the program to run.
    timeLimit: Optional[int] = 1000

    # Wall time limit in milliseconds to allow the program to run.
    wallTimeLimit: Optional[int] = 2000

    # Memory limit in MiB.
    memoryLimit: Optional[int] = 256

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
    # Command to run the program.
    command: Optional[str] = None

    # Sandbox configuration to use when executing for this language.
    sandbox: Optional[EnvironmentSandbox] = None


class EnvironmentLanguage(BaseModel):
    # Identifier of this language within this environment.
    name: str

    # File extension supported by this language. If there's only one language
    # that supports a certain file extension in the environment, the tool
    # will automatically identify the language based on such extension.
    extension: str

    # Compilation config to use when compiling programs for this language.
    compilation: Optional[CompilationConfig] = None

    # Execution config to use when running programs for this language.
    execution: ExecutionConfig


class Environment(BaseModel):
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
    languages: Optional[List[EnvironmentLanguage]] = []

    # Identifier of the sandbox used by this environment (e.g. "stupid", "isolate")
    sandbox: str
