import pathlib

from robox.config import Language, get_config
from robox.schema import Problem
from robox.submitors.codeforces import CodeforcesSubmitor

_SUBMITORS = [CodeforcesSubmitor()]


def handle_submit(file: pathlib.Path, problem: Problem, lang: Language) -> bool:
    for submitor in _SUBMITORS:
        if submitor.should_handle(problem):
            submitor_config = get_config().submitor[lang.submitor]
            credentials = get_config().credentials[submitor.key()]
            return submitor.submit(
                file, problem, submitor_config[submitor.key()], credentials
            )
    return False
