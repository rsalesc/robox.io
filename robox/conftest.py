import os
import pathlib
import tempfile
from collections.abc import Iterator

import pytest

from robox.testing_utils import get_testdata_path


@pytest.fixture
def testdata_path() -> pathlib.Path:
    return get_testdata_path()


@pytest.fixture
def cleandir() -> Iterator[pathlib.Path]:
    with tempfile.TemporaryDirectory() as newpath:
        abspath = pathlib.Path(newpath).absolute()
        old_cwd = pathlib.Path.cwd()
        os.chdir(newpath)
        try:
            yield abspath
        finally:
            os.chdir(str(old_cwd))
