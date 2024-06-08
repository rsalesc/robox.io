from functools import partial
import os
import stat
import pathlib
import resource
import select
import shutil
import subprocess
import tempfile
import logging
from time import time, monotonic
from typing import BinaryIO, List, Optional

import gevent
from ..cacher import FileCacher
from ..sandbox import SandboxBase
from codefreaker.grading.judge import sandbox

logger = logging.getLogger(__name__)


def wait_without_std(procs: List[subprocess.Popen]) -> List[int]:
    """Wait for the conclusion of the processes in the list, avoiding
    starving for input and output.

    procs (list): a list of processes as returned by Popen.

    return (list): a list of return codes.

    """

    def get_to_consume():
        """Amongst stdout and stderr of list of processes, find the
        ones that are alive and not closed (i.e., that may still want
        to write to).

        return (list): a list of open streams.

        """
        to_consume = []
        for process in procs:
            if process.poll() is None:  # If the process is alive.
                if process.stdout and not process.stdout.closed:
                    to_consume.append(process.stdout)
                if process.stderr and not process.stderr.closed:
                    to_consume.append(process.stderr)
        return to_consume

    # Close stdin; just saying stdin=None isn't ok, because the
    # standard input would be obtained from the application stdin,
    # that could interfere with the child process behaviour
    for process in procs:
        if process.stdin:
            process.stdin.close()

    # Read stdout and stderr to the end without having to block
    # because of insufficient buffering (and without allocating too
    # much memory). Unix specific.
    to_consume = get_to_consume()
    while len(to_consume) > 0:
        to_read = select.select(to_consume, [], [], 1.0)[0]
        for file_ in to_read:
            file_.read(8 * 1024)
        to_consume = get_to_consume()

    return [process.wait() for process in procs]


class StupidSandbox(SandboxBase):
    """A stupid sandbox implementation. It has very few features and
    is not secure against things like box escaping and fork
    bombs. Yet, it is very portable and has no dependencies, so it's
    very useful for testing. Using in real contests is strongly
    discouraged.

    """

    exec_num: int
    popen: Optional[subprocess.Popen]
    popen_time: Optional[float]
    exec_time: Optional[float]

    def __init__(
        self,
        file_cacher: Optional[FileCacher] = None,
        name: Optional[str] = None,
        temp_dir: pathlib.Path = None,
    ):
        """Initialization.

        For arguments documentation, see SandboxBase.__init__.

        """
        if not temp_dir:
            temp_dir = pathlib.Path(tempfile.gettempdir())
        SandboxBase.__init__(self, file_cacher, name, temp_dir)

        # Make box directory
        self._path = pathlib.Path(
            tempfile.mkdtemp(dir=str(self.temp_dir), prefix="cfk-%s-" % (self.name))
        )
        self.initialize()

        self.exec_num = -1
        self.popen = None
        self.popen_time = None
        self.exec_time = None

        logger.debug("Sandbox in `%s' created, using stupid box.", self._path)

        # Box parameters
        self.params.chdir = self._path

    def initialize(self):
        self._path.mkdir(parents=True, exist_ok=True)

    def get_root_path(self) -> pathlib.Path:
        """Return the toplevel path of the sandbox.

        return (Path): the root path.

        """
        return self._path

    # TODO - It returns wall clock time, because I have no way to
    # check CPU time (libev doesn't have wait4() support)
    def get_execution_time(self) -> float:
        """Return the time spent in the sandbox.

        return (float): time spent in the sandbox.

        """
        return self.get_execution_wall_clock_time()

    # TODO - It returns the best known approximation of wall clock
    # time; unfortunately I have no way to compute wall clock time
    # just after the child terminates, because I have no guarantee
    # about how the control will come back to this class
    def get_execution_wall_clock_time(self) -> float:
        """Return the total time from the start of the sandbox to the
        conclusion of the task.

        return (float): total time the sandbox was alive.

        """
        if self.exec_time:
            return self.exec_time
        if self.popen_time:
            self.exec_time = monotonic() - self.popen_time
            return self.exec_time
        return None

    # TODO - It always returns None, since I have no way to check
    # memory usage (libev doesn't have wait4() support)
    def get_memory_used(self) -> int:
        """Return the memory used by the sandbox.

        return (int): memory used by the sandbox (in bytes).

        """
        return None

    def get_killing_signal(self) -> int:
        """Return the signal that killed the sandboxed process.

        return (int): offending signal, or 0.

        """
        if self.popen.returncode < 0:
            return -self.popen.returncode
        return 0

    # This sandbox only discriminates between processes terminating
    # properly or being killed with a signal; all other exceptional
    # conditions (RAM or CPU limitations, ...) result in some signal
    # being delivered to the process
    def get_exit_status(self) -> str:
        """Get information about how the sandbox terminated.

        return (string): the main reason why the sandbox terminated.

        """
        if self.popen.returncode >= 0:
            return self.EXIT_OK
        else:
            return self.EXIT_SIGNAL

    def get_exit_code(self) -> int:
        """Return the exit code of the sandboxed process.

        return (float): exitcode, or 0.

        """
        return self.popen.returncode

    def get_human_exit_description(self) -> str:
        """Get the status of the sandbox and return a human-readable
        string describing it.

        return (string): human-readable explaination of why the
                         sandbox terminated.

        """
        status = self.get_exit_status()
        if status == self.EXIT_OK:
            return (
                "Execution successfully finished (with exit code %d)"
                % self.get_exit_code()
            )
        elif status == self.EXIT_SIGNAL:
            return "Execution killed with signal %s" % self.get_killing_signal()

    def _popen(
        self,
        command: List[str],
        stdin: Optional[BinaryIO] = None,
        stdout: Optional[BinaryIO] = None,
        stderr: Optional[BinaryIO] = None,
        preexec_fn=None,
        close_fds: bool = True,
    ) -> subprocess.Popen:
        """Execute the given command in the sandbox using
        subprocess.Popen, assigning the corresponding standard file
        descriptors.

        command ([string]): executable filename and arguments of the
            command.
        stdin (file|None): a file descriptor/object or None.
        stdout (file|None): a file descriptor/object or None.
        stderr (file|None): a file descriptor/object or None.
        preexec_fn (function|None): to be called just before execve()
            or None.
        close_fds (bool): close all file descriptor before executing.

        return (object): popen object.

        """
        self.exec_time = None
        self.exec_num += 1

        logger.debug(
            "Executing program in sandbox with command: `%s'.", " ".join(command)
        )
        with open(
            self.relative_path(self.cmd_file), "at", encoding="utf-8"
        ) as commands:
            commands.write("%s\n" % command)
        try:
            p = subprocess.Popen(
                command,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                preexec_fn=preexec_fn,
                close_fds=close_fds,
            )
        except OSError:
            logger.critical(
                "Failed to execute program in sandbox " "with command: `%s'.",
                " ".join(command),
                exc_info=True,
            )
            raise

        return p

    def execute_without_std(self, command: List[str], wait: bool = False) -> bool:
        """Execute the given command in the sandbox using
        subprocess.Popen and discarding standard input, output and
        error. More specifically, the standard input gets closed just
        after the execution has started; standard output and error are
        read until the end, in a way that prevents the execution from
        being blocked because of insufficient buffering.

        command ([string]): executable filename and arguments of the
            command.

        return (bool): True if the sandbox didn't report errors
            (caused by the sandbox itself), False otherwise

        """

        def preexec_fn(self: "StupidSandbox"):
            """Set limits for the child process."""
            if self.params.chdir:
                os.chdir(self.params.chdir)

            # TODO - We're not checking that setrlimit() returns
            # successfully (they may try to set to higher limits than
            # allowed to); anyway, this is just for testing
            # environment, not for real contests, so who cares.
            if self.params.timeout:
                rlimit_cpu = self.params.timeout
                if self.params.extra_timeout:
                    rlimit_cpu += self.params.extra_timeout
                rlimit_cpu = int((rlimit_cpu + 999) // 1000)
                resource.setrlimit(resource.RLIMIT_CPU, (rlimit_cpu, rlimit_cpu))

            if self.params.address_space:
                rlimit_data = self.params.address_space * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_DATA, (rlimit_data, rlimit_data))

            if self.params.stack_space:
                rlimit_stack = self.params.stack_space * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_STACK, (rlimit_stack, rlimit_stack))

            # TODO - Doesn't work as expected
            # resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))

        # Setup std*** redirection
        if self.params.stdin_file:
            stdin_fd = os.open(
                os.path.join(self._path, self.params.stdin_file), os.O_RDONLY
            )
        else:
            stdin_fd = subprocess.PIPE
        if self.params.stdout_file:
            stdout_fd = os.open(
                os.path.join(self._path, self.params.stdout_file),
                os.O_WRONLY | os.O_TRUNC | os.O_CREAT,
                stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR,
            )
        else:
            stdout_fd = subprocess.PIPE
        if self.params.stderr_file:
            if self.params.stderr_file == sandbox.MERGE_STDERR:
                stderr_fd = subprocess.STDOUT
            else:
                stderr_fd = os.open(
                    os.path.join(self._path, self.params.stderr_file),
                    os.O_WRONLY | os.O_TRUNC | os.O_CREAT,
                    stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR,
                )
        else:
            stderr_fd = subprocess.PIPE

        # Note down execution time
        self.popen_time = monotonic()

        # Actually call the Popen
        self.popen = self._popen(
            command,
            stdin=stdin_fd,
            stdout=stdout_fd,
            stderr=stderr_fd,
            preexec_fn=partial(preexec_fn, self),
            close_fds=True,
        )

        # Close file descriptors passed to the child
        if self.params.stdin_file:
            os.close(stdin_fd)
        if self.params.stdout_file:
            os.close(stdout_fd)
        if self.params.stderr_file and self.params.stderr_file != sandbox.MERGE_STDERR:
            os.close(stderr_fd)

        if self.params.wallclock_timeout:
            # Kill the process after the wall clock time passed
            def timed_killer(timeout, popen):
                gevent.sleep(timeout)
                # TODO - Here we risk to kill some other process that gets
                # the same PID in the meantime; I don't know how to
                # properly solve this problem
                try:
                    popen.kill()
                except OSError:
                    # The process had died by itself
                    pass

            # Setup the killer
            full_wallclock_timeout = self.params.wallclock_timeout
            if self.params.extra_timeout:
                full_wallclock_timeout += self.params.extra_timeout
            gevent.spawn(timed_killer, full_wallclock_timeout / 1000, self.popen)

        # If the caller wants us to wait for completion, we also avoid
        # std*** to interfere with command. Otherwise we let the
        # caller handle these issues.
        if wait:
            return self.translate_box_exitcode(wait_without_std([self.popen])[0])
        else:
            return self.popen

    def translate_box_exitcode(self, _):
        """Translate the sandbox exit code to a boolean sandbox success.

        This sandbox never fails.

        """
        return True

    def cleanup(self, delete=False):
        """See Sandbox.cleanup()."""
        # This sandbox doesn't have any cleanup, but we might want to delete.
        if delete:
            logger.debug("Deleting sandbox in %s.", self._path)
            shutil.rmtree(str(self._path))
