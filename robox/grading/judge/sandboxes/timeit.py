import dataclasses
import os
import pathlib
import resource
import signal
import sys
from math import ceil
from time import monotonic
from typing import List, Optional


@dataclasses.dataclass()
class Options:
    output_file: str
    argv: List[str]
    time_limit: Optional[float] = None
    wall_time_limit: Optional[float] = None
    memory_limit: Optional[int] = None


def exit_with(code: int):
    sys.exit(code)


def parse_opts() -> Options:
    options = Options(output_file=sys.argv[1], argv=[])
    num_opts = 0
    while num_opts + 2 < len(sys.argv) and sys.argv[num_opts + 2].startswith('-'):
        # Process option
        opt = sys.argv[num_opts + 2]
        if opt.startswith('-t'):
            options.time_limit = float(opt[2:])
        elif opt.startswith('-w'):
            options.wall_time_limit = float(opt[2:])
        elif opt.startswith('-m'):
            options.memory_limit = int(opt[2:]) * 1024
        else:
            raise Exception(f'Invalid option {opt}')
        num_opts += 1
    options.argv = sys.argv[num_opts + 2 :]
    return options


def get_memory_usage(ru: resource.struct_rusage) -> int:
    used = ceil((ru.ru_maxrss + ru.ru_ixrss + ru.ru_idrss + ru.ru_isrss) / 1024)
    return used


def get_cpu_time(ru: resource.struct_rusage) -> float:
    return ru.ru_utime + ru.ru_stime


def set_rlimits(options: Options):
    if options.time_limit is not None:
        time_limit_in_ms = int(options.time_limit * 1000)
        rlimit_cpu = int((time_limit_in_ms + 999) // 1000)
        resource.setrlimit(resource.RLIMIT_CPU, (rlimit_cpu, rlimit_cpu))


def wait_and_finish(pid: int, options: Options, start_time: float):
    _, exitstatus, ru = os.wait4(pid, 0)
    wall_time = monotonic() - start_time
    cpu_time = get_cpu_time(ru)
    memory_used = get_memory_usage(ru)

    entries = []
    exitcode = os.waitstatus_to_exitcode(exitstatus)
    entries.append(f'time: {cpu_time:.3f}')
    entries.append(f'time-wall: {wall_time:.3f}')
    entries.append(f'mem: {memory_used}')
    entries.append(f'exit-code: {exitcode}')
    if exitcode < 0:
        entries.append(f'exit-sig: {-exitcode}')

    status = set()
    if exitcode > 0:
        status.add('RE')
    if exitcode < 0:
        status.add('SG')
    if options.time_limit is not None and (
        cpu_time > options.time_limit or -exitcode == 24
    ):
        status.add('TO')
    if options.wall_time_limit is not None and wall_time > options.wall_time_limit:
        status.add('WT')
        status.add('TO')
    if options.memory_limit is not None and memory_used > options.memory_limit:
        status.add('ML')

    if status:
        status_str = ','.join(status)
        entries.append(f'status: {status_str}')

    output_file = pathlib.Path(sys.argv[1])
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text('\n'.join(entries) + '\n')


def main():
    options = parse_opts()

    start_time = monotonic()
    sub_pid = os.fork()
    if sub_pid == 0:
        # set_rlimits(options)
        os.execvp(options.argv[0], options.argv)

    def handle_alarm(*args, **kwargs):
        wall_time = monotonic() - start_time
        if options.wall_time_limit is not None and wall_time > options.wall_time_limit:
            os.kill(sub_pid, 9)
            return
        ru = resource.getrusage(resource.RUSAGE_CHILDREN)
        if options.time_limit is not None:
            cpu_time = get_cpu_time(ru)
            if cpu_time > options.time_limit:
                os.kill(sub_pid, 9)
                return
        if options.memory_limit is not None:
            memory_used = get_memory_usage(ru)
            if memory_used > options.memory_limit:
                os.kill(sub_pid, 9)
                return

        signal.alarm(1)

    signal.alarm(1)
    signal.signal(signal.SIGALRM, handle_alarm)
    wait_and_finish(sub_pid, options, start_time)


if __name__ == '__main__':
    main()
