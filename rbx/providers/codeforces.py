import re
from typing import List, Optional

from rbx.providers.provider import ProviderInterface
from rbx.schema import Problem


def _add_underscores(matches: List[str]) -> List[str]:
    if len(matches) <= 2:
        return matches
    return [f'{x}_' for x in matches[:-2]] + matches[-2:]


_PATTERNS = [
    r'https?://(?:.*\.)?codeforces.(?:com|ml|es)/(?:contest|gym)/(\d+)/problem/([^/]+)',
    r'https?://(?:.*\.)?codeforces.(?:com|ml|es)/problemset/problem/(\d+)/([^/]+)',
    (
        r'https?://(?:.*\.)?codeforces.(?:com|ml|es)/group/([^/]+)/contest/(\d+)/problem/([^/]+)',
        _add_underscores,
    ),
    r'https?://(?:.*\.)?codeforces.(?:com|ml|es)/problemset/(gym)Problem/([^/]+)',
    r'https?://(?:.*\.)?codeforces.(?:com|ml|es)/problemsets/(acm)sguru/problem/(?:\d+)/([^/]+)',
    # TODO: add EDU
]


def _compiled_pattern(pattern):
    if isinstance(pattern, tuple):
        return (re.compile(pattern[0]), pattern[1])
    return re.compile(pattern)


_COMPILED_PATTERNS = [_compiled_pattern(pattern) for pattern in _PATTERNS]


def get_code_tuple(url: str) -> Optional[List[str]]:
    for pattern_obj in _COMPILED_PATTERNS:
        if isinstance(pattern_obj, tuple):
            pattern, extract = pattern_obj
        else:
            pattern = pattern_obj
            extract = lambda x: x  # noqa: E731

        if match := pattern.match(url):
            return extract(list(match.groups()))
    return None


class CodeforcesProvider(ProviderInterface):
    def should_handle(self, url: str) -> bool:
        return 'codeforces.com/' in url

    def should_simplify_contest_problems(self) -> bool:
        return True

    def get_problem_code_within_contest(self, problem: Problem) -> str:
        return self.get_aliases(problem)[-1]

    def get_code(self, problem: Problem) -> str:
        code_tuple = get_code_tuple(problem.url)
        if not code_tuple:
            return super().get_code(problem)
        return ''.join(code_tuple)

    def get_aliases(self, problem: Problem) -> List[str]:
        code_tuple = get_code_tuple(problem.url)
        if not code_tuple:
            return super().get_aliases(problem)

        aliases = []
        for i in range(len(code_tuple)):
            aliases.append(''.join(code_tuple[i:]))
        return aliases
