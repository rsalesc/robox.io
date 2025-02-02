import atexit
import pathlib

from rich.console import Console

from rbx import grading_utils
from rbx.grading.judge import cacher, storage
from rbx.grading.judge.sandboxes.isolate import IsolateSandbox

console = Console()


def main():
    fs = storage.FilesystemStorage(pathlib.PosixPath('/tmp/rbx-storage'))
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
        cache, params=grading_utils.build_preprocess_sandbox_params(), debug=True
    )
    atexit.register(sandbox.cleanup)
    sandbox.create_file_from_storage(pathlib.PosixPath('run.cpp'), python_file)

    sandbox.params.stdout_file = pathlib.PosixPath('run.out')
    sandbox.params.stderr_file = pathlib.PosixPath('run.err')

    sandbox.execute_without_std(
        ['/usr/bin/g++', '-std=c++17', '-o', 'executable', 'run.cpp'],
    )
    try:
        sandbox.hydrate_logs()
    except Exception:
        console.print_exception()

    print(sandbox.log)
    print(sandbox.get_human_exit_description())
    print(sandbox.get_stats())

    print(sandbox.get_file_to_string(pathlib.PosixPath('run.out')))
    print(sandbox.get_file_to_string(pathlib.PosixPath('run.err')))


if __name__ == '__main__':
    main()
