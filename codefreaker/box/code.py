from pathlib import PosixPath
import pathlib
from codefreaker.box.environment import get_language
from codefreaker.box.schema import CodeItem


def get_extension(code: CodeItem) -> str:
    path: pathlib.Path = PosixPath(code.path)
    return path.suffix[1:]


def find_language_name(code: CodeItem) -> str:
    if code.language is not None:
        return get_language(code.language).name
    return get_language(get_extension(code)).name
