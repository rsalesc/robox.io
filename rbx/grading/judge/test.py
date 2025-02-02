import atexit
import pathlib

from rich.console import Console

from rbx.grading.judge import cacher, storage
from rbx.grading.judge.sandboxes import stupid_sandbox

console = Console()


def main():
    fs = storage.FilesystemStorage(pathlib.PosixPath('/tmp/rbx-storage'))
    cache = cacher.FileCacher(fs)

    python_file = cache.put_file_text("print('hello')")

    sandbox = stupid_sandbox.StupidSandbox(cache)
    atexit.register(sandbox.cleanup)
    sandbox.create_file_from_storage(pathlib.PosixPath('run.py'), python_file)

    sandbox.params.stdout_file = pathlib.PosixPath('run.out')

    sandbox.execute_without_std(['ls'])
    try:
        sandbox.hydrate_logs()
    except Exception:
        console.print_exception()

    print(sandbox.get_human_exit_description())
    print(sandbox.get_stats())
    print(sandbox.log)

    print(sandbox.get_file_to_string(pathlib.PosixPath('run.out')))


if __name__ == '__main__':
    main()
