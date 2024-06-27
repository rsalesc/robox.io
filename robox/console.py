import sys

from rich.console import Console
from rich.theme import Theme

theme = Theme(
    {
        'default': 'bright_white',
        'rbx': 'bold italic yellow',
        'info': 'bright_black',
        'status': 'bright_white',
        'item': 'bold blue',
        'error': 'bold red',
        'success': 'bold green',
        'lnumber': 'dim cyan',
        'warning': 'bold yellow',
    }
)
console = Console(theme=theme, style='info', highlight=False)
stderr_console = Console(theme=theme, style='info', highlight=False, stderr=True)


def multiline_prompt(text: str) -> str:
    console.print(f'{text} (Ctrl-D to finish):\n')
    lines = sys.stdin.readlines()
    console.print()
    return ''.join(lines)
