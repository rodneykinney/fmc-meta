from typing import Optional, Dict, List, Tuple, Callable
from collections import defaultdict

from py_cubelib import Algorithm, StepInfo, debug


class SolutionBuilder:
    def __init__(
            self,
            kind: str = "",
            variant: str = "",
            previous: Optional["SolutionBuilder"] = None,
            comment="",
    ):
        self.kind = kind
        self.variant = variant
        self.step_info = StepInfo(kind, variant)
        self.previous = previous
        self.alg = Algorithm("")
        self.is_checked = False
        self.comment = comment

    def append_moves(self, moves: List[str], inverse: bool) -> bool:
        if not all(self.allows_move(m) for m in moves):
            return False

        for m in moves:
            self._add_move(m, inverse)
        update(_current)
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

    def substeps(self) -> List["SolutionBuilder"]:
        if self.previous is None:
            return [self]
        else:
            return self.previous.substeps() + [self]

    def back(self):
        if self.previous is None:
            update(SolutionBuilder())
            return

        previous = self.previous.previous or SolutionBuilder()

        previous.advance_to(self.previous.kind, self.previous.variant)



    def reset(self):
        new_current = SolutionBuilder(self.kind, self.variant, previous=self.previous, comment=self.comment)
        update(new_current)

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
        previous = self if not self.alg.is_empty() else self.previous
        self.is_checked = True
        update(SolutionBuilder(kind, variant, previous=previous))

    def append_comment(self, str):
        self.comment = f"{self.comment}{' ' if self.comment else ''}{str}"

    def saved_solutions_of_same_step(self) -> List["SolutionBuilder"]:
        return _steps[(self.kind, self.variant)]

    def clear(self):
        _steps.clear()
        update(SolutionBuilder("", "", previous=None))

    def load(self, index: int):
        l = _steps.get((self.kind, self.variant), list())
        if l and index <= len(l):
            update(l[index])



# Nested dict of (kind,variant) => SolutionBuilder
_steps: Dict[Tuple[str, str], List[SolutionBuilder]] = defaultdict(list)
# The algorithm currently being built
_current: SolutionBuilder = SolutionBuilder("", "")
_listener: Optional[Callable[[SolutionBuilder, SolutionBuilder], None]] = None
def update(new_current):
    global _current
    old_current = _current
    _current = new_current
    if _listener is not None:
        _listener(old_current, new_current)

