import importlib
import importlib.resources
import pathlib

import rich.tree
import rich.text
import rich.markup
from rich.filesize import decimal

from codefreaker import console

_TESTDATA_PKG = 'testdata'


def get_testdata_path() -> pathlib.Path:
    with importlib.resources.as_file(
        importlib.resources.files(_TESTDATA_PKG) / 'compatible'
    ) as file:
        return file.parent


def clear_all_functools_cache():
    from codefreaker.box import environment, package

    pkgs = [environment, package]

    for pkg in pkgs:
        for fn in pkg.__dict__.values():
            if hasattr(fn, 'cache_clear'):
                fn.cache_clear()


def walk_directory(directory: pathlib.Path, tree: rich.tree.Tree) -> None:
    """Recursively build a Tree with directory contents."""
    # Sort dirs first then by filename
    paths = sorted(
        pathlib.Path(directory).iterdir(),
        key=lambda path: (path.is_file(), path.name.lower()),
    )
    for path in paths:
        # Remove hidden files
        if path.name.startswith('.'):
            continue
        if path.is_dir():
            style = 'dim' if path.name.startswith('__') else ''
            branch = tree.add(
                f'[bold magenta]:open_file_folder: [link file://{path}]{rich.markup.escape(path.name)}',
                style=style,
                guide_style=style,
            )
            walk_directory(path, branch)
        else:
            text_filename = rich.text.Text(path.name, 'green')
            text_filename.highlight_regex(r'\..*$', 'bold red')
            text_filename.stylize(f'link file://{path}')
            file_size = path.stat().st_size
            text_filename.append(f' ({decimal(file_size)})', 'blue')
            icon = '🐍 ' if path.suffix == '.py' else '📄 '
            tree.add(rich.text.Text(icon) + text_filename)


def print_directory_tree(directory: pathlib.Path):
    tree = rich.tree.Tree(directory.name)
    walk_directory(directory, tree)
    console.console.print(tree)
