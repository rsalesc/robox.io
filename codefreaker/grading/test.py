import pathlib
from . import storage
from . import cacher
from .sandboxes import stupid_sandbox


def main():
    fs = storage.FilesystemStorage(pathlib.PosixPath("/tmp/cfk-storage"))
    cache = cacher.FileCacher(fs)

    python_file = cache.put_file_text("print('hello')")

    sandbox = stupid_sandbox.StupidSandbox(cache)
    sandbox.create_file_from_storage(pathlib.PosixPath("run.py"), python_file)

    sandbox.stdout_file = "run.out"

    sandbox.execute_without_std(["python3", "run.py"], wait=True)

    print(sandbox.get_human_exit_description())
    print(sandbox.get_stats())

    print(sandbox.get_file_to_string(pathlib.PosixPath("run.out")))


if __name__ == "__main__":
    main()
