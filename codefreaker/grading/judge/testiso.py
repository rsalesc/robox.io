import atexit
import pathlib

from rich.console import Console

from codefreaker.grading import steps
from codefreaker.grading.judge.sandbox import SandboxParams
from codefreaker.grading.judge.sandboxes.isolate import IsolateSandbox
from . import storage
from . import cacher

console = Console()


def main():
    fs = storage.FilesystemStorage(pathlib.PosixPath("/tmp/cfk-storage"))
    cache = cacher.FileCacher(fs)

    python_file = cache.put_file_text(
        """
#include <bits/stdc++.h>
 
int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;                                      
}
"""
    )

    sandbox = IsolateSandbox(
        cache, params=steps.get_preprocess_sandbox_params(None), debug=True
    )
    atexit.register(sandbox.cleanup)
    sandbox.create_file_from_storage(pathlib.PosixPath("run.cpp"), python_file)

    sandbox.params.stdout_file = "run.out"
    sandbox.params.stderr_file = "run.err"

    sandbox.execute_without_std(["/usr/bin/g++", "run.cpp"], wait=True)
    try:
        sandbox.hydrate_logs()
    except Exception:
        console.print_exception()

    print(sandbox.log)
    print(sandbox.get_human_exit_description())
    print(sandbox.get_stats())

    print(sandbox.get_file_to_string(pathlib.PosixPath("run.out")))


if __name__ == "__main__":
    main()
