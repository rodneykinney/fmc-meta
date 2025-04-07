from typing import Optional, Dict, List, Callable
from collections import defaultdict

from py_cubelib import Algorithm, StepInfo, debug, Cube


class PartialSolution:
    def __init__(
            self,
            kind: str = "",
            variant: str = "",
            alg: Algorithm = Algorithm(""),
            previous: Optional["PartialSolution"] = None,
            comment="",
    ):
        self.kind = kind
        self.variant = variant
        self.step_info = StepInfo(kind, variant)
        self.previous = previous
        self.alg = alg
        self.comment = comment or self.kind

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

    def substeps(self) -> List["PartialSolution"]:
        if self.previous is None:
            return [self]
        else:
            return self.previous.substeps() + [self]

    def is_empty(self) -> bool:
        val = self.alg.is_empty()
        if self.previous:
            val = val and self.previous.is_empty()
        return val

    def __repr__(self):
        return f"{self.alg} // {self.comment} ({self.full_alg().len()})"



class Attempt:
    def __init__(self):
        self.scramble = ""
        self.cube = Cube("")
        self.inverse = False
        self.solution = PartialSolution()
        self._saved_by_kind: Dict[str, List[PartialSolution]] = defaultdict(list)
        self._cube_listeners = []
        self._solution_listeners = []

    def set_scramble(self, s):
        self.clear()
        self.scramble = s
        self.update_cube()

    def set_inverse(self, b):
        self.inverse = b
        self.update_cube()

    def append_moves(self, moves: List[str], inverse: bool) -> bool:
        if not all(self.solution.allows_move(m) for m in moves):
            return False

        for m in moves:
            self.solution._add_move(m, inverse)
        self.update_cube()
        return True

    def back(self):
        if self.solution.previous is None:
            self.set_solution(PartialSolution())
            return

        previous = self.solution.previous
        self.solution = previous.previous or PartialSolution()

        self.advance_to(previous.kind, previous.variant)

    def advance_to(self, kind: str, variant: str):
        previous = self.solution if not self.solution.alg.is_empty() else self.solution.previous
        self.set_solution(PartialSolution(kind, variant, previous=previous))

    def solutions_by_kind(self) -> Dict[str, List[PartialSolution]]:
        return self._saved_by_kind

    def solutions_for_step(self, kind: str, variant: str) -> List[PartialSolution]:
        return [s for s in self._saved_by_kind.get(kind, []) if s.variant == s.variant]

    def reset(self):
        alg = self.solution.alg
        # Clear only the moves for the current side
        if self.inverse:
            alg = Algorithm(" ".join(alg.normal_moves()))
        else:
            alg = Algorithm(f"({' '.join(alg.inverse_moves())})")
        new_solution = PartialSolution(
            self.solution.kind,
            self.solution.variant,
            previous=self.solution.previous,
            alg = alg,
            comment=self.solution.comment
        )
        self.set_solution(new_solution)

    def set_solution(self, sol: PartialSolution):
        self.solution = sol
        self.update_cube()

    def save(self):
        self.save_solution(self.solution)

    def save_solution(self, sol: PartialSolution):
        self.save_solutions([sol])

    def save_solutions(self, sols: List[PartialSolution]):
        new_sols_by_key = defaultdict(list)
        for s in sols:
            new_sols_by_key[s.kind].append(s)
        for kind, sols_for_kind in new_sols_by_key.items():
            existing = self._saved_by_kind[kind]
            existing_algs = set(str(s.full_alg()) for s in existing)
            existing += [s for s in sols_for_kind if not str(s.full_alg()) in existing_algs]
            existing.sort(key=lambda s: (s.alg.len(), s.variant))
        for l in self._solution_listeners:
            l()

    def clear(self):
        self._saved_by_kind.clear()
        self.scramble = ""
        self.set_solution(PartialSolution("", "", previous=None))

    def add_solution_listener(self, callback: Callable):
        self._solution_listeners.append(callback)

    def add_cube_listener(self, callback: Callable):
        self._cube_listeners.append(callback)

    def update_cube(self):
        self.cube = Cube(self.scramble)
        self.cube.apply(self.solution.full_alg())
        if self.inverse:
            self.cube.invert()
        for l in self._cube_listeners:
            l()

