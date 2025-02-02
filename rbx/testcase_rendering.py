import dataclasses
import pathlib
import string
from typing import List, Tuple

from rich.text import Text


@dataclasses.dataclass
class TruncatedOutput:
    truncate: bool = False
    lines: List[Tuple[int, str]] = dataclasses.field(default_factory=list)


def split_and_truncate_in_lines(
    s: str, max_line_length: int = 64, max_lines: int = 30
) -> TruncatedOutput:
    lines: List[Tuple[int, str]] = []
    current_line = []
    current_line_idx = 1

    def end_line(wrap: bool = False):
        nonlocal current_line, current_line_idx
        lines.append((current_line_idx, ''.join(current_line)))
        current_line = []
        if not wrap:
            current_line_idx += 1

    printable = set(string.printable)
    truncate = False
    for c in s:
        if c == '\n':
            end_line()
            continue
        if c not in printable:
            # TODO: handle better
            continue
        if len(current_line) >= max_line_length:
            end_line(wrap=True)
        if current_line_idx > max_lines:
            truncate = True
            break
        current_line.append(c)

    if current_line:
        end_line()

    return TruncatedOutput(truncate=truncate, lines=lines)


def _largest_line_number_length(lines: List[Tuple[int, str]]) -> int:
    return max([len(str(line[0])) for line in lines] + [1])


def render(s: str):
    truncated = split_and_truncate_in_lines(s)
    number_len = _largest_line_number_length(truncated.lines)

    text = Text()

    last_number = 0
    for line in truncated.lines:
        number, content = line
        number_str = '' if last_number == number else str(number)
        text.append(f'{number_str:>{number_len}}', style='lnumber')
        text.append(' ' * 3)
        text.append(content)
        text.append('\n')

        last_number = number
    if truncated.truncate:
        text.append(f"{'':>{number_len}}", style='lnumber')
        text.append(' ' * 3)
        text.append('... (truncated)')
    return text


def render_from_file(file: pathlib.Path):
    return render(file.read_text())
