import atexit
import pathlib

from rich.console import Console

from codefreaker.grading.judge import cacher, storage
from codefreaker.grading.judge.sandboxes import stupid_sandbox

console = Console()


def main():
    fs = storage.FilesystemStorage(pathlib.PosixPath('/tmp/cfk-storage'))
    cache = cacher.FileCacher(fs)

    python_file = cache.put_file_text("print('hello')")

    sandbox = stupid_sandbox.StupidSandbox(cache)
    atexit.register(sandbox.cleanup)
    sandbox.create_file_from_storage(pathlib.PosixPath('run.py'), python_file)

    sandbox.params.stdout_file = 'run.out'

    sandbox.execute_without_std(['python3', 'run.py'], wait=True)
    try:
        sandbox.hydrate_logs()
    except Exception as e:
        console.print_exception(e)

    print(sandbox.get_human_exit_description())
    print(sandbox.get_stats())

    print(sandbox.get_file_to_string(pathlib.PosixPath('run.out')))


if __name__ == '__main__':
    main()
