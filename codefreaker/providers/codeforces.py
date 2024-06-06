import re

from typing import List, Optional, Set, Tuple
from codefreaker.providers.provider import ProviderInterface
from codefreaker.schema import Problem

_PATTERNS = [
    r"https?://(?:.*\.)?codeforces.com/(contest|gym)/(\d+)/problem/([^/]+)",
]

_COMPILED_PATTERNS = [re.compile(pattern) for pattern in _PATTERNS]


def get_code_tuple(url: str) -> List[str]:
    for pattern_obj in _COMPILED_PATTERNS:
        if isinstance(pattern_obj, tuple):
            pattern, extract = pattern_obj
        else:
            pattern = pattern_obj
            extract = lambda x: x

        if match := pattern.match(url):
            return extract(list(match.groups()[1:]))
    return None


class CodeforcesProvider(ProviderInterface):
    def should_handle(self, url: str) -> bool:
        return "codeforces.com/" in url

    def get_code(self, problem: Problem) -> str:
        code_tuple = get_code_tuple(problem.url)
        if not code_tuple:
            return super().get_code(problem)
        return "".join(code_tuple)

    def get_aliases(self, problem: Problem) -> List[str]:
        code_tuple = get_code_tuple(problem.url)
        if not code_tuple:
            return super().add_aliases(problem)

        aliases = []
        for i in range(len(code_tuple)):
            aliases.append("".join(code_tuple[i:]))
        return aliases
