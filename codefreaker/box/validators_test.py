import pathlib
import pytest

from codefreaker.box.validators import validate_testcases
from codefreaker.box.generators import generate_testcases
from codefreaker.testing_utils import print_directory_tree


@pytest.mark.test_pkg("box1")
def test_validators(pkg_from_testdata: pathlib.Path):
    generate_testcases()
    validation_infos = validate_testcases()

    for info in validation_infos:
        assert info.ok
