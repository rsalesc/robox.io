import pathlib

from codefreaker.grading.judge.sandbox import SandboxParams
from codefreaker.grading.judge.sandboxes.isolate import IsolateSandbox
from . import storage
from . import cacher


def main():
    fs = storage.FilesystemStorage(pathlib.PosixPath("/tmp/cfk-storage"))
    cache = cacher.FileCacher(fs)

    python_file = cache.put_file_text("print('hello')")

    sandbox = IsolateSandbox(cache, params=SandboxParams(cgroup=False))
    sandbox.create_file_from_storage(pathlib.PosixPath("run.py"), python_file)

    sandbox.params.stdout_file = "run.out"
    sandbox.params.stderr_file = "run.err"

    sandbox.maybe_add_mapped_directory(pathlib.PosixPath("/usr"))
    sandbox.maybe_add_mapped_directory(pathlib.PosixPath("/etc"))
    sandbox.execute_without_std(["/usr/bin/python3", "run.py"], wait=True)
    sandbox.get_log()

    print(sandbox.log)
    print(sandbox.get_human_exit_description())
    print(sandbox.get_stats())

    print(sandbox.get_file_to_string(pathlib.PosixPath("run.out")))


if __name__ == "__main__":
    main()
