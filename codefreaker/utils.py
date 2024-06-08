import json
import pathlib
from typing import Any, Optional

from pydantic import BaseModel
import rich
import rich.prompt
import rich.status
from rich import text
from rich.highlighter import JSONHighlighter

from .console import console


def create_and_write(path: pathlib.Path, *args, **kwargs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(*args, **kwargs)


def highlight_str(s: str) -> text.Text:
    txt = text.Text(s)
    JSONHighlighter().highlight(txt)
    return txt


def highlight_json_obj(obj: Any) -> text.Text:
    js = json.dumps(obj)
    return highlight_str(js)


def normalize_with_underscores(s: str) -> str:
    res = s.replace(" ", "_").replace(".", "_").strip("_")
    final = []

    last = ""
    for c in res:
        if c == "_" and last == c:
            continue
        last = c
        final.append(c)
    return "".join(final)


def model_json(model: BaseModel) -> str:
    return model.model_dump_json(indent=4, exclude_unset=True, exclude_none=True)


def confirm_on_status(status: Optional[rich.status.Status], *args, **kwargs) -> bool:
    if status:
        status.stop()
    res = rich.prompt.Confirm.ask(*args, **kwargs, console=console)
    if status:
        status.start()
    return res
