import dataclasses
import pathlib
import typing
from enum import Enum
from typing import Callable, List, Optional

import lark
import typer

from robox import console
from robox.box import package
from robox.box.schema import CodeItem, ExpectedOutcome
from robox.grading.steps import CheckerResult, Outcome, RunLog

LARK_GRAMMAR = r"""
// A bunch of words
start: disjunction

disjunction: conjunction | disjunction _OR conjunction

conjunction: _atom | conjunction _AND _atom

_atom: statement | "(" disjunction ")" | negation
negation: _NOT "(" disjunction ")"

statement: solution matcher outcome checking?

solution: _filename | WILDCARD
outcome: CNAME
checking: "ON"i (checking_mode? checker | ":nil")
checking_mode: MODE ":"
MODE: "2" | "3"
checker: _filename | WILDCARD

// Operators
matcher: MATCHES | NOT_MATCHES

MATCHES: "~"
NOT_MATCHES: "!~"
_OR: "||"
_AND: "&&"
_NOT: "!"
WILDCARD: "$"

// File name
_filename: FILENAME | "\"" FILENAME "\""
FILENAME: /[\/A-Za-z0-9\-_\.]/+

%import common.CNAME
%ignore " "
"""

LARK_PARSER = lark.Lark(LARK_GRAMMAR)


class CheckingMode(Enum):
    THREE_WAY = 0
    TWO_WAY = 1


@dataclasses.dataclass(frozen=True)
class FinderChecker:
    path: str
    mode: CheckingMode


@dataclasses.dataclass(frozen=True)
class FinderCall:
    solution: str
    expected_outcome: ExpectedOutcome
    checker: Optional[FinderChecker]


@dataclasses.dataclass(frozen=True)
class FinderSolutionResult:
    output_path: pathlib.Path
    stderr_path: Optional[pathlib.Path] = None
    run_log: Optional[RunLog] = None


@dataclasses.dataclass(frozen=True)
class FinderResult:
    solution: str
    outcome: Outcome
    checker: Optional[FinderChecker]
    truth_value: bool

    # Auxiliary information.
    solution_result: Optional[FinderSolutionResult] = None
    checker_result: Optional[CheckerResult] = None


@dataclasses.dataclass(frozen=True)
class FinderOutcome:
    truth_value: bool
    results: List[FinderResult]


def or_outcome(a: FinderOutcome, b: FinderOutcome) -> FinderOutcome:
    return FinderOutcome(
        truth_value=a.truth_value or b.truth_value, results=a.results + b.results
    )


def and_outcome(a: FinderOutcome, b: FinderOutcome) -> FinderOutcome:
    return FinderOutcome(
        truth_value=a.truth_value and b.truth_value, results=a.results + b.results
    )


def get_checking_mode_from_string(mode: Optional[str]) -> CheckingMode:
    if not mode:
        return CheckingMode.THREE_WAY
    if mode == '2':
        return CheckingMode.TWO_WAY
    return CheckingMode.THREE_WAY


def _get_main_checker() -> Optional[str]:
    pkg = package.find_problem_package_or_die()
    if not pkg.checker:
        return None
    return str(pkg.checker.path)


def _get_main_solution() -> Optional[str]:
    sol = package.get_main_solution()
    if sol is None:
        return None
    return str(sol.path)


def _get_default_checker_for_finder() -> Optional[FinderChecker]:
    main_checker = _get_main_checker()
    if main_checker is None:
        return None
    return FinderChecker(path=main_checker, mode=CheckingMode.THREE_WAY)


def _get_solution_from_token(token: lark.Token) -> str:
    path = str(token)
    if path == '$':
        main_path = _get_main_solution()
        assert main_path is not None
        return main_path
    return path


def _get_checker_from_token(token: lark.Token) -> str:
    path = str(token)
    if path == '$':
        main_path = _get_main_checker()
        assert main_path is not None
        return main_path
    return path


def _get_statement_checker(statement: lark.ParseTree) -> Optional[FinderChecker]:
    checking_nodes = list(statement.find_data('checking'))
    if not checking_nodes:
        return _get_default_checker_for_finder()
    (checking,) = checking_nodes

    if not checking.children:
        # Checking is nil
        return None

    if len(checking.children) == 1:
        checker = typing.cast(lark.ParseTree, checking.children[0])
        return FinderChecker(
            path=_get_checker_from_token(typing.cast(lark.Token, checker.children[0])),
            mode=CheckingMode.THREE_WAY,
        )

    mode = typing.cast(lark.ParseTree, checking.children[0])
    checker = typing.cast(lark.ParseTree, checking.children[1])

    return FinderChecker(
        path=_get_checker_from_token(typing.cast(lark.Token, checker.children[0])),
        mode=get_checking_mode_from_string(
            typing.cast(lark.Token, mode.children[0]).value
        ),
    )


def get_all_solutions(tree: lark.ParseTree) -> List[str]:
    solution_nodes = tree.find_data('solution')
    res = set(
        [
            _get_solution_from_token(typing.cast(lark.Token, node.children[0]))
            for node in solution_nodes
        ]
    )

    if needs_expected_output(tree):
        main_solution = package.get_main_solution()
        assert main_solution is not None
        res.add(str(main_solution.path))
    return list(res)


def get_all_solution_items(tree: lark.ParseTree) -> List[CodeItem]:
    solution_names = get_all_solutions(tree)
    res = []

    for solution_name in solution_names:
        found_solution = package.get_solution_or_nil(solution_name)
        if found_solution is None:
            res.append(
                CodeItem(
                    path=pathlib.Path(solution_name),
                    language=None,
                    compilationFiles=None,
                )
            )
            continue
        res.append(found_solution)

    main_solution = package.get_main_solution()
    if main_solution is None:
        return res

    for i, sol in enumerate(res):
        if main_solution.path == sol.path:
            res[i], res[0] = res[0], res[i]
    return res


def _get_all_finder_checkers(tree: lark.ParseTree) -> List[FinderChecker]:
    statement_nodes = tree.find_data('statement')
    res = []

    for statement_node in statement_nodes:
        finder_checker = _get_statement_checker(statement_node)
        if finder_checker is not None:
            res.append(finder_checker)

    return res


def get_all_checkers(tree: lark.ParseTree) -> List[str]:
    return [finder_checker.path for finder_checker in _get_all_finder_checkers(tree)]


def get_all_checker_items(tree: lark.ParseTree) -> List[CodeItem]:
    checker_names = get_all_checkers(tree)
    res = []

    for checker_name in checker_names:
        main_checker = package.get_checker()
        if str(main_checker.path) == checker_name:
            res.append(main_checker)
            continue
        res.append(
            CodeItem(
                path=pathlib.Path(checker_name),
                language=None,
                compilationFiles=None,
            )
        )
    return res


def needs_expected_output(tree: lark.ParseTree) -> bool:
    finder_checkers = _get_all_finder_checkers(tree)
    for finder_checker in finder_checkers:
        if finder_checker.mode == CheckingMode.THREE_WAY:
            return True
    return False


def validate(tree: lark.ParseTree):
    if needs_expected_output(tree):
        if package.get_main_solution() is None:
            console.console.print(
                '[error]Finder expression requires three-way checking, but problem has no main solution.[/error]'
            )
            console.console.print(
                'Either provide an ACCEPTED solution at your problem.rbx.yml, or use two-way checking in your finder expression by providing the `2:` parameter before the checker name.'
            )
            raise typer.Exit(1)

    all_checkers = get_all_checkers(tree)
    for checker in all_checkers:
        if not pathlib.Path(checker).is_file():
            console.console.print(
                f'[error]Finder expression references non-existing checker [item]{checker}[/item].[/error]'
            )
            raise typer.Exit(1)

    all_solutions = get_all_solutions(tree)
    for solution in all_solutions:
        if not pathlib.Path(solution).is_file():
            console.console.print(
                f'[error]Finder expression references non-existing solution [item]{solution}[/item].[/error]'
            )
            raise typer.Exit(1)


@lark.v_args(inline=True)
class FinderTreeRunner(lark.Transformer):
    outcome = ExpectedOutcome

    def __init__(
        self,
        runner: Callable[[FinderCall], FinderResult],
    ):
        self.run_fn = runner

    def solution(self, token: lark.Token) -> str:
        return _get_solution_from_token(token)

    def matcher(self, op: lark.Token) -> bool:
        return op.value == '~'

    @lark.v_args(inline=False, tree=True)
    def statement(
        self,
        tree: lark.ParseTree,
    ) -> FinderOutcome:
        solution = typing.cast(str, tree.children[0])
        is_positive = typing.cast(bool, tree.children[1])
        expected_outcome = typing.cast(ExpectedOutcome, tree.children[2])

        checker: Optional[FinderChecker] = _get_statement_checker(tree)

        call = FinderCall(solution, expected_outcome=expected_outcome, checker=checker)
        result = self.run_fn(call)
        truth_value = result.truth_value
        if not is_positive:
            truth_value = not truth_value

        return FinderOutcome(truth_value=truth_value, results=[result])

    def negation(self, value: FinderOutcome) -> FinderOutcome:
        return dataclasses.replace(value, truth_value=not value.truth_value)

    @lark.v_args(inline=False)
    def conjunction(self, values: List[FinderOutcome]) -> FinderOutcome:
        res = FinderOutcome(truth_value=True, results=[])
        for value in values:
            res = and_outcome(res, value)
        return res

    @lark.v_args(inline=False)
    def disjunction(self, values: List[FinderOutcome]) -> FinderOutcome:
        res = FinderOutcome(truth_value=False, results=[])
        for value in values:
            res = or_outcome(res, value)
        return res

    def start(self, value: FinderOutcome) -> FinderOutcome:
        return value


def parse(expression: str) -> lark.ParseTree:
    tree = LARK_PARSER.parse(expression)
    validate(tree)
    return tree
