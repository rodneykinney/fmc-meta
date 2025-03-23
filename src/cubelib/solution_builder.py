from typing import Optional, Dict, List, Tuple
from collections import defaultdict

from py_cubelib import Solution, SolutionStep, Algorithm, StepInfo, debug


class SolutionBuilder:
    def __init__(
            self,
            kind: str = "",
            variant: str = "",
            previous: Optional["SolutionBuilder"] = None,
            listener=None
    ):
        self.kind = kind
        self.variant = variant
        self.step_info = StepInfo(kind, variant)
        self.previous = previous
        self.moves = []
        self.listener = listener

    def append_moves(self, moves: List[str]) -> bool:
        if not all(self.allows_move(m) for m in moves):
            return False

        for m in moves:
            self._add_move(m)
        self.notify()
        return True

    def _add_move(self, move: str):
        if self.moves and self.moves[-1][0] == move[0]:
            suffixes = {self.moves[-1][1:], move[1:]}
            if suffixes == {"", ""} or suffixes == {"'", "'"}:
                self.moves[-1] = f"{move[0]}2"
            elif suffixes == {"'", ""} or suffixes == {"2", "2"}:
                self.moves.pop()
            elif suffixes == {"", "2"}:
                self.moves[-1] = f"{move[0][0]}'"
            elif suffixes == {"'", "2"}:
                self.moves[-1] = move[0][:1]
            else:
                raise ValueError(f"Could not combine {move} with {self.moves[-1]}")
        else:
            self.moves.append(move)

    def allows_move(self, move: str) -> bool:
        if self.previous is None:
            return True
        return self.previous.step_info.is_move_allowed(move)

    def all_moves(self):
        if self.previous is not None:
            return self.previous.all_moves() + self.moves
        return self.moves

    def build(self) -> Solution:
        sol = Solution()
        if self.previous is not None:
            sol = self.previous.build()
        sol.append(SolutionStep(
            kind=self.kind,
            variant=self.variant,
            alg=" ".join(self.moves),
            comment="")
        )
        return sol

    def back(self):
        global _builder

        if self.previous is None:
            _builder = SolutionBuilder(listener=self.listener)
            self.notify()
            return

        previous = self.previous.previous or SolutionBuilder(listener=self.listener)

        previous.advance_to(self.previous.kind, self.previous.variant)


    def notify(self):
        if self.listener is not None:
            self.listener(_builder)

    def reset(self):
        global _builder
        _builder = SolutionBuilder(self.kind, self.variant, previous=self.previous, listener=self.listener)
        self.notify()

    def save(self):
        _steps[(self.kind, self.variant)].append(self)

    def advance_to(self, kind: str, variant: str):
        global _builder
        previous = self if self.moves else self.previous
        _builder = SolutionBuilder(kind, variant, previous=previous, listener=self.listener)
        self.notify()

    def saved_solutions_of_same_step(self) -> List["SolutionBuilder"]:
        return _steps[(self.kind, self.variant)]

    def clear(self):
        global _builder
        _steps.clear()
        _builder = SolutionBuilder("", "", previous=None, listener=self.listener)
        self.notify()

    def load(self, index: int):
        global _builder
        l = _steps.get((self.kind, self.variant), list())
        if l and index <= len(l):
            _builder = l[index]
            self.notify()



# Nested dict of (kind,variant) => SolutionBuilder
_steps: Dict[Tuple[str, str], List[SolutionBuilder]] = defaultdict(list)
# The algorithm currently being built
_builder: SolutionBuilder = SolutionBuilder("", "")
