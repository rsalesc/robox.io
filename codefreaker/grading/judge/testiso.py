import atexit
import pathlib

from rich.console import Console

from codefreaker.grading.judge.sandbox import SandboxParams
from codefreaker.grading.judge.sandboxes.isolate import IsolateSandbox
from . import storage
from . import cacher

console = Console()


def main():
    fs = storage.FilesystemStorage(pathlib.PosixPath("/tmp/cfk-storage"))
    cache = cacher.FileCacher(fs)

    python_file = cache.put_file_text("print('hello')")

    IsolateSandbox.next_id = 5
    sandbox = IsolateSandbox(cache, params=SandboxParams(cgroup=False))
    atexit.register(sandbox.cleanup)
    sandbox.create_file_from_storage(pathlib.PosixPath("run.py"), python_file)

    sandbox.params.stdout_file = "run.out"
    sandbox.params.stderr_file = "run.err"

    sandbox.maybe_add_mapped_directory(pathlib.PosixPath("/usr"))
    sandbox.maybe_add_mapped_directory(pathlib.PosixPath("/etc"))
    sandbox.execute_without_std(["/usr/bin/python3", "run.py"], wait=True)
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
