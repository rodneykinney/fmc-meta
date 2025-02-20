import dataclasses
from typing import List, Tuple, Optional
import random
import hashlib

from pydantic import BaseModel, Field

from fmc_meta import (
    Step,
    EOStrategy,
    DRStrategy,
    FinishStrategy,
    Meta,
    nissy,
)


class GeneralEO(EOStrategy, BaseModel):
    max_eo_length: int = Field(default=5, description="Maximum move count")
    retain: int = Field(default=30, description="Attempt to find DR on this many EOs")
    check_inverse: bool = Field(
        default=True, description="Check both normal and inverse"
    )
    max_niss_split: int = Field(
        default=1, description="Maximum number of moves before NISS"
    )
    seed: Optional[int] = Field(None, description="Random seed")

    def description(self) -> str:
        lines = [
            f"All EOs up to {self.max_eo_length} moves",
        ]
        if not self.check_inverse:
            lines.append("Dont check inverse")
        if self.max_niss_split > 0:
            lines.append(f"Allow up to {self.max_niss_split} pre-moves")
        lines.append(f"Choose {self.retain} for DR attempt")
        return ". ".join(lines)

    @property
    def salt(self):
        return (
            hex(random.Random(self.seed).randint(0, 0xFFFFFFFFFFFFFFFF))
            if self.seed
            else ""
        )

    def find_eos_on_axis(self, axis_step: str, scramble: Step) -> List[Step]:
        all_eos = []
        args = ["-M", self.max_eo_length]
        if self.check_inverse and self.max_niss_split > 0:
            args.append("-N")
        eos = nissy(axis_step, scramble, *args)
        if self.check_inverse and self.max_niss_split > 0:
            eos = [
                s
                for s in eos
                if min(len(s.moves), len(s.moves_on_inverse)) <= self.max_niss_split
            ]
            all_eos.extend(eos)
        elif self.check_inverse:
            all_eos.extend(eos)
            found_eos = set(str(s) for s in all_eos)
            i_eos = nissy(axis_step, scramble.on_inverse(), *args)
            i_eos = [
                Step(name=s.name, previous=scramble, moves_on_inverse=s.moves)
                for s in i_eos
                if not str(s.on_inverse()) in found_eos
            ]
            all_eos.extend(i_eos)
        return all_eos

    def sort_order(self, step: Step) -> Tuple:
        return (
            step.cumulative_move_count,
            step.includes_niss,
            step.requires_niss,
            hashlib.sha1((str(step) + self.salt).encode("UTF8")).hexdigest(),
        )

    def select_eos(self, eos: List[Step]) -> List[Step]:
        eos = sorted(eos, key=self.sort_order)
        eos = eos[: self.retain]
        return eos


class DRHelper(BaseModel):
    check_inverse: bool = Field(
        default=True, description="Check both normal and inverse"
    )
    max_niss_split: int = Field(
        default=0, description="Maximum number of moves before NISS"
    )
    seed: Optional[int] = Field(default=None, description="Random seed")

    @property
    def eo_to_dr_stages(self):
        return {
            "eofb": ["drud-eofb", "drrl-eofb"],
            "eorl": ["drud-eorl", "drfb-eorl"],
            "eoud": ["drfb-eoud", "drrl-eoud"],
        }

    @property
    def salt(self):
        return (
            hex(random.Random(self.seed).randint(0, 0xFFFFFFFFFFFFFFFF))
            if self.seed
            else ""
        )

    def sort_order(self, step: Step) -> Tuple:
        return (
            step.cumulative_move_count,
            step.includes_niss,
            step.requires_niss,
            hashlib.sha1((str(step) + self.salt).encode("UTF8")).hexdigest(),
        )

    def order_drs(self, drs: List[Step]) -> List[Step]:
        return sorted(drs, key=self.sort_order)

    def find_drs_for_eo(self, eo: Step, budget: int) -> List[Step]:
        all_drs = []
        for next_step in self.eo_to_dr_stages[eo.name]:
            args = ["-M", budget + 1]  # Allow one extra in case of cancellation

            if self.check_inverse and self.max_niss_split > 0:
                args.append("-N")
            drs = nissy(next_step, eo, *args)
            drs = [s for s in drs if s.move_count <= budget]
            if self.check_inverse and self.max_niss_split > 0:
                drs = [s for s in drs if s.move_count <= budget]
                drs = [
                    s
                    for s in drs
                    if min(len(s.moves), len(s.moves_on_inverse)) <= self.max_niss_split
                ]
                all_drs.extend(drs)
            elif self.check_inverse:
                # This is faster than running nissy -N
                all_drs.extend(drs)
                i_drs = nissy(next_step, eo.on_inverse(), *args)
                i_drs = [s for s in i_drs if s.move_count <= budget]
                i_drs = [
                    Step(name=s.name, previous=eo, moves_on_inverse=s.moves)
                    for s in i_drs
                ]
                all_drs.extend(i_drs)

        return all_drs


class OptimalDR(DRStrategy, BaseModel):
    max_dr_length: int = Field(default=12, description="Maximum move count")
    include_eo_move_count: bool = Field(
        default=True, description="Include EO when checking maximum move count"
    )
    retain: int = Field(default=10, description="Attempt to finish this many DRs")
    check_inverse: bool = Field(
        default=True, description="Check both normal and inverse"
    )
    seed: Optional[int] = Field(default=None, description="Random seed")

    def description(self) -> str:
        lines = []
        if self.include_eo_move_count:
            lines.append(
                f"Optimal DR, without breaking EO, up to {self.max_dr_length} moves, including EO"
            )
        else:
            lines.append(
                f"Optimal DR, without breaking EO, up to {self.max_dr_length}, not including EO"
            )
        if not self.check_inverse:
            lines.append("Dont check inverse")
        lines.append(f"Choose {self.retain} for finish attempt")
        return ". ".join(lines)

    @property
    def helper(self):
        return DRHelper(
            check_inverse=self.check_inverse,
            max_niss_split=0,
            seed=self.seed,
        )

    def find_drs_for_eo(self, eo: Step) -> List[Step]:
        budget = self.max_dr_length - (
            eo.move_count if self.include_eo_move_count else 0
        )
        return self.helper.find_drs_for_eo(eo, budget)

    def select_drs(self, drs: List[Step]) -> List[Step]:
        return self.helper.order_drs(drs)[: self.retain]


class SingleAxisDR(DRStrategy, BaseModel):
    max_dr_length: int = Field(
        default=14, description="Maximum move count, including EO"
    )
    retain: int = Field(default=10, description="Attempt to finish this many DRs")
    check_inverse: bool = Field(
        default=True, description="Check both normal and inverse"
    )
    seed: Optional[int] = Field(default=None, description="Random seed")

    def description(self) -> str:
        lines = []
        lines.append(
            f"Intuitively findable DRs (pure rzp or jzp), up to {self.max_dr_length} moves, including EO"
        )
        if not self.check_inverse:
            lines.append("Don't check inverse")
        lines.append(f"Choose {self.retain} for finish attempt")
        return ". ".join(lines)

    @property
    def helper(self):
        return DRHelper(
            check_inverse=self.check_inverse,
            max_niss_split=0,
            seed=self.seed,
        )

    def is_findable(self, step: Step) -> bool:
        moves = step.moves if step.moves else step.moves_on_inverse
        # Count distinct axes having a quarter turn, up until the final quarter turn
        moves = moves[:-1]
        qts = set(
            m.replace("'", "").replace("L", "R").replace("D", "U").replace("B", "F")
            for m in moves
            if "2" not in m
        )
        return len(qts) == 1

    def find_drs_for_eo(self, eo: Step) -> List[Step]:
        budget = self.max_dr_length - eo.move_count
        drs = self.helper.find_drs_for_eo(eo, budget)
        drs = list(filter(self.is_findable, drs))
        return drs

    def select_drs(self, drs: List[Step]) -> List[Step]:
        return self.helper.order_drs(drs)[: self.retain]


class OptimalFinish(FinishStrategy, BaseModel):

    def description(self) -> str:
        lines = []
        lines.append(f"Optimal finish without breaking DR")
        return ". ".join(lines)

    def dr_to_finish(self, dr: Step) -> List[Step]:
        finish_step = f"{dr.name.split('-')[0]}fin"
        shortest = nissy(finish_step, dr)[0]
        if shortest.move_count < len(shortest.moves):
            # Already have a cancellation
            return [shortest]
        else:
            # Search for equal/longer finishes that may have cancellations
            finishes = nissy(finish_step, dr, "-M", len(shortest.moves) + 1)
            finishes.sort(key=lambda f: f.cumulative_move_count)
            return finishes[:1]


class EasyCornerOnlyFinish(FinishStrategy, BaseModel):
    max_qt_count: int = Field(
        default=3, description="Don't attempt DR cases with more than this many QTs"
    )

    def description(self) -> str:
        lines = []
        lines.append(f"Optimal finish with <= {self.max_qt_count} QTs, not breaking DR")
        return ". ".join(lines)

    def dr_to_finish(self, dr: Step) -> List[Step]:
        finish_step = f"{dr.name.split('-')[0]}fin"
        shortest = nissy(finish_step, dr)[0]
        if shortest.qt_count <= self.max_qt_count:
            if shortest.move_count < len(shortest.moves):
                # Already have a cancellation
                return [shortest]
            else:
                # Search for equal/longer finishes that may have cancellations
                finishes = nissy(finish_step, dr, "-M", len(shortest.moves) + 1)
                finishes.sort(key=lambda f: f.cumulative_move_count)
                return [f for f in finishes if f.qt_count <= self.max_qt_count][:1]
        else:
            # Too many QTs. Search for solutions up to two moves longer
            finishes = nissy(finish_step, dr, "-M", len(shortest.moves) + 2)
            finishes.sort(key=lambda f: f.cumulative_move_count)

            return [f for f in finishes if f.qt_count <= self.max_qt_count][:1]
