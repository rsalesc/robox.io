import os
import pathlib
import shutil

import pytest

from codefreaker.box import package
from codefreaker.box.generators import generate_testcases
from codefreaker.testing_utils import print_directory_tree


@pytest.mark.test_pkg("box1")
def test_generator_compilation(pkg_from_testdata: pathlib.Path):
    generate_testcases()
    assert (package.get_build_testgroup_path("gen1") / "000.in").read_text() == "777\n"
    assert (package.get_build_testgroup_path("gen1") / "001.in").read_text() == "123\n"

    # Debug when fail.
    print_directory_tree(pkg_from_testdata)


@pytest.mark.test_pkg("box1")
def test_generator_compilation_does_not_cache_on_change(
    pkg_from_testdata: pathlib.Path,
):
    # Run the first time.
    generate_testcases()
    assert (package.get_build_testgroup_path("gen1") / "001.in").read_text() == "123\n"
    # Change the generator.
    gen_path = pkg_from_testdata / "gen1.cpp"
    gen_path.write_text(gen_path.read_text().replace("123", "4567"))
    # Run the second time.
    generate_testcases()
    assert (package.get_build_testgroup_path("gen1") / "001.in").read_text() == "4567\n"

    # Debug when fail.
    print_directory_tree(pkg_from_testdata)
