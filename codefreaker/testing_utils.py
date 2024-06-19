import importlib
import importlib.resources
import pathlib

_TESTDATA_PKG = "testdata"


def get_testdata_path() -> pathlib.Path:
    with importlib.resources.as_file(
        importlib.resources.files(_TESTDATA_PKG) / "compatible"
    ) as file:
        return file.parent
