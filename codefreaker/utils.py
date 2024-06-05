import pathlib

def create_and_write(path: pathlib.Path, *args, **kwargs):
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(*args, **kwargs)