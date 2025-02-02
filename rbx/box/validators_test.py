import pathlib

import pytest

from rbx.box.generators import generate_testcases
from rbx.box.validators import validate_testcases


@pytest.mark.test_pkg('box1')
def test_validators(pkg_from_testdata: pathlib.Path):
    generate_testcases()
    validation_infos = validate_testcases()

    for info in validation_infos:
        assert info.ok
