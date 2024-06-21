import pathlib
import pytest

from codefreaker.box.solutions import run_solutions
from codefreaker.box.generators import (
    generate_outputs_for_testcases,
    generate_testcases,
)
from codefreaker.grading.steps import Outcome


@pytest.mark.test_pkg("box1")
def test_solutions(pkg_from_testdata: pathlib.Path):
    generate_testcases()
    generate_outputs_for_testcases()

    res = run_solutions()

    # First solution should pass all tests.
    assert all(chk.outcome == Outcome.ACCEPTED for chk in res[0]["gen1"])
    # 25 test should be WA for the second solution.
    assert res[1]["gen1"][3].outcome == Outcome.WRONG_ANSWER
    # Runtime error for third solution.
    assert all(chk.outcome == Outcome.RUNTIME_ERROR for chk in res[2]["gen1"])
    # 1e9 test should be TLE for the fourth solution (soft TLE)
    assert res[3]["gen1"][4].outcome == Outcome.TIME_LIMIT_EXCEEDED
    # no TLE outcome should be WA (soft TLE)
    assert res[4]["gen1"][4].no_tle_outcome == Outcome.WRONG_ANSWER
    # hard TLE
    assert res[5]["gen1"][4].outcome in [
        Outcome.RUNTIME_ERROR,
        Outcome.TIME_LIMIT_EXCEEDED,
    ]
