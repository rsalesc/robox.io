import pathlib
import itertools
from typing import Optional

import rich
import rich.prompt
import rich.status

from .console import console

def create_and_write(path: pathlib.Path, *args, **kwargs):
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(*args, **kwargs)

def normalize_with_underscores(s: str) -> str:
  res = s.replace(' ', '_').replace('.', '_').strip('_')
  final = []

  last = ''
  for c in res:
    if c == '_' and last == c:
      continue
    last = c
    final.append(c)
  return ''.join(final)

def confirm_on_status(status: Optional[rich.status.Status], *args, **kwargs) -> bool:
  if status:
    status.stop()
  res = rich.prompt.Confirm.ask(*args, **kwargs, console=console)
  if status:
    status.start()
  return res