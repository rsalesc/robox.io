import dataclasses
from enum import Enum
from typing import Callable, List, Optional

import lark

from robox.box.schema import ExpectedOutcome
from robox.grading.steps import Outcome

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
checking: "ON"i checking_mode? checker
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


@dataclasses.dataclass
class FinderChecker:
    path: str
    mode: CheckingMode


@dataclasses.dataclass
class FinderCall:
    solution: str
    expected_outcome: ExpectedOutcome
    checker: Optional[FinderChecker]


@dataclasses.dataclass
class FinderResult:
    solution: str
    outcome: Outcome
    checker: Optional[FinderChecker]
    truth_value: bool


@dataclasses.dataclass
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


@lark.v_args(inline=True)
class FinderTreeRunner(lark.Transformer):
    solution = str
    checking_mode = str
    checker = str
    outcome = ExpectedOutcome

    def __init__(
        self,
        runner: Callable[[FinderCall], FinderResult],
    ):
        self.run_fn = runner

    def matcher(self, op: lark.Token) -> bool:
        return op.value == '~'

    def checking(self, *args) -> FinderChecker:
        mode = None
        if len(args) == 2:
            mode, checker = args
        else:
            checker = args[0]

        parsed_mode = get_checking_mode_from_string(mode)
        return FinderChecker(path=checker, mode=parsed_mode)

    def statement(
        self, solution: str, is_positive: bool, expected_outcome: ExpectedOutcome, *args
    ) -> FinderOutcome:
        checker: Optional[FinderChecker] = None
        if len(args) == 1:
            checker = args[0]

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
        res = FinderOutcome(truth_value=False, results=[])
        for value in values:
            res = and_outcome(res, value)
        return res

    @lark.v_args(inline=False)
    def disjunction(self, values: List[FinderOutcome]) -> FinderOutcome:
        res = FinderOutcome(truth_value=True, results=[])
        for value in values:
            res = or_outcome(res, value)
        return res

    def start(self, value: FinderOutcome) -> FinderOutcome:
        return value


def parse(expression: str) -> lark.ParseTree:
    tree = LARK_PARSER.parse(expression)
    return tree


if __name__ == '__main__':

    def _dummy_run(call: FinderCall) -> FinderResult:
        return FinderResult(
            call.solution,
            outcome=Outcome.ACCEPTED,
            checker=call.checker,
            truth_value=True,
        )

    tree = parse('!($ ~ accepted ON 3:$ && oba.cpp ~ WRONG_ANSWER)')
    transformed_tree = FinderTreeRunner(_dummy_run).transform(tree)
    print(tree)
    print('---')
    print(transformed_tree)
