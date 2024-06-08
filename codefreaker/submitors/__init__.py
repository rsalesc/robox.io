import pathlib
from codefreaker.config import Language, get_config
from codefreaker.schema import Problem
from codefreaker.submitors.codeforces import CodeforcesSubmitor


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
