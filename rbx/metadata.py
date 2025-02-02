import pathlib
from typing import List, Optional, Tuple

from rbx.schema import DumpedProblem


def _normalize_alias(alias: str) -> str:
    return alias.lower()


def _find_alias(alias: str, haystack: List[str]) -> Optional[int]:
    normalized_alias = _normalize_alias(alias)
    for i, candidate in enumerate(haystack):
        if _normalize_alias(candidate) == normalized_alias:
            return i
    return None


def _get_best_alias_from_candidates(
    alias: str, candidates: List[Tuple[pathlib.Path, DumpedProblem]]
) -> Optional[Tuple[pathlib.Path, DumpedProblem]]:
    best_priority = 1e9
    best_candidates = []
    for path, problem in candidates:
        index = _find_alias(alias, problem.aliases)
        if index is None:
            continue
        if index < best_priority:
            best_priority = index
            best_candidates = [(path, problem)]
        elif index == best_priority:
            best_candidates.append((path, problem))

    if len(best_candidates) != 1:
        # TODO
        return None

    return best_candidates[0]


def find_problem_path_by_code(
    code: str, root: Optional[pathlib.Path] = None
) -> Optional[pathlib.Path]:
    if not root:
        root = pathlib.Path()

    metadata_path = root / f'{code}.rbx.json'
    if not metadata_path.is_file():
        return None
    return metadata_path


def find_problem_path_by_alias(
    alias: str, root: Optional[pathlib.Path] = None
) -> Optional[pathlib.Path]:
    if not root:
        root = pathlib.Path()

    candidates: List[Tuple[pathlib.Path, DumpedProblem]] = []
    for metadata_path in root.glob('*.rbx.json'):
        problem = DumpedProblem.model_validate_json(metadata_path.read_text())
        if _find_alias(alias, problem.aliases) is not None:
            candidates.append((metadata_path, problem))

    picked_candidate = _get_best_alias_from_candidates(alias, candidates)
    if not picked_candidate:
        return None
    return picked_candidate[0]


def find_problem_by_alias(
    alias: str, root: Optional[pathlib.Path] = None
) -> Optional[DumpedProblem]:
    metadata_path = find_problem_path_by_alias(alias, root)
    if not metadata_path:
        return None
    return DumpedProblem.model_validate_json(metadata_path.read_text())


def find_problem_by_code(
    code: str, root: Optional[pathlib.Path] = None
) -> Optional[DumpedProblem]:
    metadata_path = find_problem_path_by_code(code, root)
    if not metadata_path:
        return None
    return DumpedProblem.model_validate_json(metadata_path.read_text())


def find_problem_by_anything(
    anything: str, root: Optional[pathlib.Path] = None
) -> Optional[DumpedProblem]:
    problem = find_problem_by_code(anything, root)
    if problem:
        return problem
    return find_problem_by_alias(anything, root)


def find_problems(root: Optional[pathlib.Path] = None) -> List[DumpedProblem]:
    if not root:
        root = pathlib.Path()

    problems = []
    for metadata_path in root.glob('*.rbx.json'):
        problems.append(DumpedProblem.model_validate_json(metadata_path.read_text()))
    return problems
