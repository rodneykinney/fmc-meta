from typing import Optional, Dict, List, Tuple, Callable
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
        self.is_checked = False
        self.comment = comment

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

    def append_comment(self, comment):
        self.comment = f"{self.comment}{' ' if self.comment else ''}{comment}"

    def __repr__(self):
        return f"{self.alg} // {self.kind}{self.variant} ({self.full_alg().len()})"



class Attempt:
    def __init__(self):
        self.scramble = ""
        self.cube = Cube("")
        self.inverse = False
        self.solution = PartialSolution()
        self._saved: Dict[str, PartialSolution] = {}
        self._listeners = []

    def set_scramble(self, s):
        self.clear()
        self.scramble = s
        self.notify()

    def set_inverse(self, b):
        self.inverse = b
        self.notify()

    def append_moves(self, moves: List[str], inverse: bool) -> bool:
        if not all(self.solution.allows_move(m) for m in moves):
            return False

        for m in moves:
            self.solution._add_move(m, inverse)
        self.notify()
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
        self.solution.is_checked = True
        self.set_solution(PartialSolution(kind, variant, previous=previous))

    def saved_solutions(self) -> Dict[str, List["PartialSolution"]]:
        dict: Dict[str, List["PartialSolution"]] = defaultdict(list)
        for sol in self._saved.values():
            dict[sol.kind].append(sol)
        for sols in dict.values():
            sols.sort(key = lambda s: (s.alg.len(), s.kind))
        return dict

    def variants_with_saved_solutions(self, kind) -> List[str]:
        return [variant for (kind, variant), l in self._saved.items() if l]

    def reset(self):
        new_solution = PartialSolution(
            self.solution.kind,
            self.solution.variant,
            previous=self.solution.previous,
            comment=self.solution.comment
        )
        self.set_solution(new_solution)

    def set_solution(self, sol: PartialSolution):
        self.solution = sol
        self.notify()

    def save(self):
        self.save_solution(self.solution)

    def save_solution(self, sol: PartialSolution):
        self._saved[str(sol)] = sol

    def clear(self):
        self._saved.clear()
        self.scramble = ""
        self.set_solution(PartialSolution("", "", previous=None))

    def load(self, solution_str: str):
        sol = self._saved.get(solution_str)
        if sol:
            self.set_solution(sol)

    def listen_to(self, callback: Callable):
        self._listeners.append(callback)

    def notify(self):
        self.cube = Cube(self.scramble)
        self.cube.apply(self.solution.full_alg())
        if self.inverse:
            self.cube.invert()
        for l in self._listeners:
            l()

