from rich.console import Console
from rich.theme import Theme
import sys

theme = Theme(
    {
        "cfk": "bold italic yellow",
        "info": "bright_black",
        "status": "bright_white",
        "item": "bold blue",
        "error": "bold red",
    }
)
console = Console(theme=theme, style="info", highlight=False)


def multiline_prompt(text: str) -> str:
    console.print(f"{text} (Ctrl-D to finish):\n")
    lines = sys.stdin.readlines()
    console.print()
    return "".join(lines)
