from __future__ import annotations

import logging
import os
import pathlib
import resource
import shutil
import stat
import subprocess
import tempfile
from functools import partial
from sys import platform
from time import monotonic
from typing import IO, List, Optional, Union

import gevent

from robox.grading.judge import sandbox
from robox.grading.judge.cacher import FileCacher
from robox.grading.judge.sandbox import (
    SandboxBase,
    SandboxParams,
    wait_without_std,
)

logger = logging.getLogger(__name__)


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
        temp_dir: Optional[pathlib.Path] = None,
        params: Optional[SandboxParams] = None,
    ):
        """Initialization.

        For arguments documentation, see SandboxBase.__init__.

        """
        if not temp_dir:
            temp_dir = pathlib.Path(tempfile.gettempdir())
        SandboxBase.__init__(self, file_cacher, name, temp_dir, params)

        # Make box directory
        self._path = pathlib.Path(
            tempfile.mkdtemp(dir=str(self.temp_dir), prefix='rbx-%s-' % (self.name))
        )
        self.initialize()

        self.exec_num = -1
        self.popen = None
        self.popen_time = None
        self.exec_time = None

        logger.debug("Sandbox in `%s' created, using stupid box.", self._path)

        # Box parameters
        self.chdir = self._path

    def initialize(self):
        self._path.mkdir(parents=True, exist_ok=True)

    def get_root_path(self) -> pathlib.Path:
        """Return the toplevel path of the sandbox.

        return (Path): the root path.

        """
        return self._path

    # TODO - It returns wall clock time, because I have no way to
    # check CPU time (libev doesn't have wait4() support)
    def get_execution_time(self) -> Optional[float]:
        """Return the time spent in the sandbox.

        return (float): time spent in the sandbox.

        """
        return self.get_execution_wall_clock_time()

    # TODO - It returns the best known approximation of wall clock
    # time; unfortunately I have no way to compute wall clock time
    # just after the child terminates, because I have no guarantee
    # about how the control will come back to this class
    def get_execution_wall_clock_time(self) -> Optional[float]:
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

    def use_soft_timeout(self) -> bool:
        if platform == 'darwin':
            return False
        return True

    # TODO - It always returns None, since I have no way to check
    # memory usage (libev doesn't have wait4() support)
    def get_memory_used(self) -> Optional[int]:
        """Return the memory used by the sandbox.

        return (int): memory used by the sandbox (in bytes).

        """
        return None

    def get_killing_signal(self) -> int:
        """Return the signal that killed the sandboxed process.

        return (int): offending signal, or 0.

        """
        assert self.popen is not None
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
        assert self.popen
        if self.popen.returncode >= 0:
            return self.EXIT_OK
        else:
            if -self.popen.returncode == 24:
                return self.EXIT_TIMEOUT
            return self.EXIT_SIGNAL

    def get_exit_code(self) -> int:
        """Return the exit code of the sandboxed process.

        return (float): exitcode, or 0.

        """
        assert self.popen
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
                'Execution successfully finished (with exit code %d)'
                % self.get_exit_code()
            )
        elif status == self.EXIT_SIGNAL:
            return 'Execution killed with signal %s' % self.get_killing_signal()
        return ''

    def hydrate_logs(self):
        return

    def _popen(
        self,
        command: List[str],
        stdin: Optional[IO[bytes] | int] = None,
        stdout: Optional[IO[bytes] | int] = None,
        stderr: Optional[IO[bytes] | int] = None,
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
            "Executing program in sandbox with command: `%s'.", ' '.join(command)
        )
        with open(
            self.relative_path(self.cmd_file), 'at', encoding='utf-8'
        ) as commands:
            commands.write('%s\n' % command)
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
                'Failed to execute program in sandbox ' "with command: `%s'.",
                ' '.join(command),
                exc_info=True,
            )
            raise

        return p

    def execute_without_std(
        self, command: List[str], wait: bool = False
    ) -> Union[bool, subprocess.Popen]:
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

        def preexec_fn(self: 'StupidSandbox'):
            """Set limits for the child process."""
            if self.chdir:
                os.chdir(self.chdir)

            if platform == 'darwin':
                # These RLimits do not work properly on macOS.
                return

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
            with self.popen as p:
                # Ensure popen fds are closed.
                res = self.translate_box_exitcode(wait_without_std([p])[0])
                # Ensure exec time is computed.
                self.get_execution_wall_clock_time()
                return res
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
            logger.debug('Deleting sandbox in %s.', self._path)
            shutil.rmtree(str(self._path))
