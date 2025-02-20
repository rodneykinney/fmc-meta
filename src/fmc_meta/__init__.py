import dataclasses
from typing import Optional, List, Tuple, Dict
from abc import ABC, abstractmethod
import multiprocessing
import functools
import subprocess
import re

from pydantic import BaseModel, Field

_pool: multiprocessing.Pool = None  # type: ignore

inverse = {
    "U": "U'",
    "U'": "U",
    "D": "D'",
    "D'": "D",
    "F": "F'",
    "F'": "F",
    "B": "B'",
    "B'": "B",
    "R": "R'",
    "R'": "R",
    "L": "L'",
    "L'": "L",
}


def invert(moves: List[str]) -> List[str]:
    return [inverse.get(m, m) for m in reversed(moves)]


class Step(BaseModel):
    name: str
    moves: List[str] = Field(default_factory=list)  # on normal
    moves_on_inverse: List[str] = Field(default_factory=list)
    previous: Optional["Step"] = None

    @property
    def all_moves(self) -> List[str]:
        prev_moves = self.previous.all_moves if self.previous else []
        moves = invert(self.moves_on_inverse) + prev_moves + self.moves
        return moves

    def on_inverse(self) -> "Step":
        return Step(
            name="inverse",
            moves=invert(self.all_moves),
            moves_on_inverse=[],
            previous=None,
        )

    @property
    def cumulative_move_count(self) -> int:
        if self.previous is None:
            return 0
        return self.previous.cumulative_move_count + self.move_count

    @property
    def move_count(self):
        count = len(self.moves) + len(self.moves_on_inverse)

        # Check for cancellations (but not against scramble)
        def cancellation(a: str, b: str):
            if a[0] == b[0]:
                if inverse.get(a, a) == b:
                    return 2
                else:
                    return 1
            return 0

        latest = self.previous
        last_move_on_normal = ""
        last_move_on_inverse = ""
        while latest.cumulative_move_count:  # not the scramble
            if latest.moves and not last_move_on_normal:
                last_move_on_normal = latest.moves[-1]
            if latest.moves_on_inverse and not last_move_on_inverse:
                last_move_on_inverse = latest.moves_on_inverse[-1]
            if last_move_on_inverse and last_move_on_normal:
                break
            latest = latest.previous
        if last_move_on_normal and self.moves:
            count -= cancellation(self.moves[0], last_move_on_normal)
        if last_move_on_inverse and self.moves_on_inverse:
            count -= cancellation(self.moves_on_inverse[0], last_move_on_inverse)
        if last_move_on_inverse and self.moves:
            count -= cancellation(self.moves[-1], last_move_on_inverse)

        return count

    @property
    def qt_count(self) -> int:
        return sum(1 for m in self.moves if not "2" in m)

    @property
    def includes_niss(self) -> bool:
        return len(self.moves) > 0 and len(self.moves_on_inverse) > 0

    @property
    def requires_niss(self) -> bool:
        if self.previous is None:
            return False
        elif self.previous.includes_niss:
            return False
        else:
            return not (len(self.moves) > 0 ^ len(self.previous.moves) > 0)

    def from_beginning(self) -> List["Step"]:
        steps = []
        s = self
        while s.previous:
            steps.append(s)
            s = s.previous
        steps.reverse()
        return steps

    def __str__(self):
        normal_moves = " ".join(self.moves)
        inverse_moves = (
            f"({' '.join(self.moves_on_inverse)})" if self.moves_on_inverse else ""
        )
        if normal_moves and inverse_moves:
            return " ".join((normal_moves, inverse_moves))
        elif normal_moves:
            return normal_moves
        else:
            return inverse_moves


class MoveCountHistogram(BaseModel):
    steps: List[Step]

    @property
    def counts(self) -> List[Tuple[int, int]]:
        count: Dict[int, int] = {}
        for s in self.steps:
            count[s.cumulative_move_count] = count.get(s.cumulative_move_count, 0) + 1
        rows = sorted(list(count.items()))
        return rows

    def __str__(self):
        return " ".join(f"{n}x{m}-moves" for m, n in self.counts)


class EOStrategy(ABC):

    @abstractmethod
    def description(self) -> str:
        pass

    def find_eos(self, scramble: Step) -> List[Step]:
        eos = [
            s
            for scramble_to_eos in _pool.map(  # type: ignore[attr-defined]
                functools.partial(self.find_eos_on_axis, scramble=scramble),
                ["eofb", "eorl", "eoud"],
            )
            for s in scramble_to_eos
        ]
        print(f"Found EOs: {MoveCountHistogram(steps=eos)}")
        eos = self.select_eos(eos)
        return eos

    @abstractmethod
    def find_eos_on_axis(self, axis_step: str, scramble: Step) -> List[Step]:
        pass

    @abstractmethod
    def select_eos(self, eos: List[Step]) -> List[Step]:
        pass


class DRStrategy(ABC):
    @abstractmethod
    def description(self):
        pass

    def find_drs(self, eos: List[Step]) -> List[Step]:
        drs = [
            s for eo_to_drs in _pool.map(self.find_drs_for_eo, eos) for s in eo_to_drs  # type: ignore[attr-defined]
        ]
        print(f"Found DRs: {MoveCountHistogram(steps=drs)}")
        return self.select_drs(drs)

    @abstractmethod
    def find_drs_for_eo(self, eo: Step) -> List[Step]:
        pass

    @abstractmethod
    def select_drs(self, drs: List[Step]) -> List[Step]:
        pass


class FinishStrategy(ABC):
    @abstractmethod
    def description(self):
        pass

    def drs_to_finishes(self, drs: List[Step]) -> List[Step]:
        finishes = [
            s
            for finishes in _pool.map(  # type: ignore[attr-defined]
                self.dr_to_finish, drs
            )
            for s in finishes
        ]
        finishes.sort(key=lambda s: s.cumulative_move_count)
        s = self.dr_to_finish(drs[0])
        return finishes

    @abstractmethod
    def dr_to_finish(self, dr: Step) -> List[Step]:
        pass


@dataclasses.dataclass
class Meta:
    eo: EOStrategy
    dr: DRStrategy
    finish: FinishStrategy


NISSY_PATH = subprocess.check_output(["which", "nissy"], encoding="UTF8").strip()


def nissy(step_name: str, scramble: Step, *args) -> List[Step]:
    cmd = (
        [NISSY_PATH, "solve", step_name, "-p"]
        + list(str(a) for a in args)
        + [" ".join(scramble.all_moves)]
    )
    p = subprocess.run(
        cmd, encoding="UTF8", stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if p.stderr:
        raise Exception(p.stderr)
    steps = []
    for line in p.stdout.strip().split("\n"):
        if not line:
            continue  # No solution
        n_i_moves: Tuple = ([], [])  # (normal,inverse)
        toggle = 0
        for move in re.split("[() ]", line):
            if move == "":  # Open or close parenthesis
                toggle = 1 - toggle
            else:
                n_i_moves[toggle].append(move)
        # Empty move list means this is a skip-step
        step = Step(
            name=step_name,
            moves=n_i_moves[0],
            moves_on_inverse=n_i_moves[1],
            previous=scramble,
        )
        steps.append(step)
    return steps
