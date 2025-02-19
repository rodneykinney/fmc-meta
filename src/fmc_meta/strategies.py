import dataclasses
from typing import List, Tuple, Optional
import random

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
    seed: Optional[int] = Field(default=None, description="Random seed")

    @property
    def rand(self):
        return random.Random(self.seed) if self.seed else random.Random()

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
            self.rand.uniform(0, 1),
        )

    def select_eos(self, eos: List[Step]) -> List[Step]:
        eos.sort(key=self.sort_order)
        eos = eos[: self.retain]
        return eos


class DRBaseStrategy(DRStrategy):

    @property
    def eo_to_dr_stages(self):
        return {
            "eofb": ["drud-eofb", "drrl-eofb"],
            "eorl": ["drud-eorl", "drfb-eorl"],
            "eoud": ["drfb-eoud", "drrl-eoud"],
        }

    @property
    def rand(self):
        return random.Random(self.seed) if self.seed else random.Random()

    def sort_order(self, step: Step) -> Tuple:
        return (
            step.cumulative_move_count,
            step.includes_niss,
            step.requires_niss,
            self.rand.uniform(0, 1),
        )

    def select_drs(self, drs: List[Step]) -> List[Step]:
        drs.sort(key=self.sort_order)
        drs = drs[: self.retain]  # type: ignore[attr-defined]
        return drs


class OptimalDR(DRBaseStrategy, BaseModel):
    max_dr_length: int = Field(default=12, description="Maximum move count")
    retain: int = Field(default=10, description="Attempt to finish this many DRs")
    check_inverse: bool = Field(
        default=True, description="Check both normal and inverse"
    )
    max_niss_split: int = Field(
        default=0, description="Maximum number of moves before NISS"
    )
    seed: Optional[int] = Field(default=None, description="Random seed")

    def find_drs_for_eo(self, eo: Step) -> List[Step]:
        budget = self.max_dr_length - eo.cumulative_move_count
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


class SingleAxisDR(DRBaseStrategy, BaseModel):
    max_dr_length: int = Field(default=12, description="Maximum move count")
    retain: int = Field(default=10, description="Attempt to finish this many DRs")
    check_inverse: bool = Field(
        default=True, description="Check both normal and inverse"
    )
    seed: Optional[int] = Field(default=None, description="Random seed")

    def find_drs_for_eo(self, eo: Step) -> List[Step]:
        return OptimalDR(
            max_dr_length=self.max_dr_length, check_inverse=self.check_inverse
        ).find_drs_for_eo(eo)

    def select_drs(self, drs: List[Step]) -> List[Step]:
        drs.sort(key=self.sort_order)

        def is_findable(step: Step) -> bool:
            moves = step.moves if step.moves else step.moves_on_inverse
            # Count distinct axes having a quarter turn, up until the final quarter turn
            moves = moves[:-1]
            qts = set(
                m.replace("'", "").replace("L", "R").replace("D", "U").replace("B", "F")
                for m in moves
                if "2" not in m
            )
            return len(qts) == 1

        drs = list(filter(is_findable, drs))[: self.retain]
        return drs


class OptimalFinish(FinishStrategy, BaseModel):
    def dr_to_finish(self, dr: Step) -> List[Step]:
        finish_step = f"{dr.name.split('-')[0]}fin"
        return nissy(finish_step, dr)[:1]


class EasyCornerOnlyFinish(FinishStrategy, BaseModel):
    max_qt_count: int = Field(
        default=3, description="Don't attempt DR cases with more than this many QTs"
    )
    max_length: int = Field(default=15, description="Maximum move count")

    def dr_to_finish(self, dr: Step) -> List[Step]:
        finish_step = f"{dr.name.split('-')[0]}fin"
        finishes = nissy(finish_step, dr, "-M", self.max_length)

        def qt_count(step: Step) -> int:
            return sum(1 for m in step.moves if not "2" in m)

        return [f for f in finishes if qt_count(f) <= self.max_qt_count][:1]
