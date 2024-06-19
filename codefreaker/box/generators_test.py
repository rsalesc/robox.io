import pathlib
import shutil

import pytest

from codefreaker.box import package
from codefreaker.box.generators import compile_generators


@pytest.mark.test_pkg("box1")
def test_generator_compilation(pkg_from_testdata):
    assert "gen1" in compile_generators()
