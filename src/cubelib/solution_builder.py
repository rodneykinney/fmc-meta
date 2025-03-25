from typing import Optional, Dict, List, Tuple
from collections import defaultdict

from py_cubelib import Algorithm, StepInfo, debug


class SolutionBuilder:
    def __init__(
            self,
            kind: str = "",
            variant: str = "",
            previous: Optional["SolutionBuilder"] = None,
            listener=None,
            comment="",
    ):
        self.kind = kind
        self.variant = variant
        self.step_info = StepInfo(kind, variant)
        self.previous = previous
        self.listener = listener
        self.alg = Algorithm("")
        self.is_checked = False
        self.comment = comment

    def append_moves(self, moves: List[str], inverse: bool) -> bool:
        if not all(self.allows_move(m) for m in moves):
            return False

        for m in moves:
            self._add_move(m, inverse)
        self.notify()
        return True

    def _add_move(self, move: str, inverse: bool):
        self.alg = self.alg.append(move, inverse)

    def allows_move(self, move: str) -> bool:
        if self.previous is None:
            return True
        return self.previous.step_info.is_move_allowed(move)

    def full_alg(self):
        if self.previous is not None:
            return self.previous.full_alg().merge(self.alg)
        return self.alg

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
        _builder = SolutionBuilder(self.kind, self.variant, previous=self.previous, listener=self.listener, comment=self.comment)
        self.notify()

    def save(self) -> bool:
        existing = _steps[(self.kind, self.variant)]
        if f"{self.alg}" in [f"{b.alg}" for b in existing]:
            return False
        existing.append(self)
        return True

    def save_solution(self, alg: Algorithm):
        existing = _steps[(self.kind, self.variant)]
        if f"{alg}" in [f"{b.alg}" for b in existing]:
            return False
        b = SolutionBuilder(
                kind=self.kind,
                variant=self.variant,
                previous=self.previous,
                listener=self.listener
            )
        b.alg = alg
        existing.append(b)
        return True


    def is_empty(self) -> bool:
        val = self.alg.is_empty()
        if self.previous:
            val = val and self.previous.is_empty()
        return val

    def advance_to(self, kind: str, variant: str):
        global _builder
        previous = self if not self.alg.is_empty() else self.previous
        _builder = SolutionBuilder(kind, variant, previous=previous, listener=self.listener)
        self.is_checked = True
        self.notify()

    def append_comment(self, str):
        self.comment = f"{self.comment}{' ' if self.comment else ''}{str}"

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
