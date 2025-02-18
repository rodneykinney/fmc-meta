from typing import List, Tuple
import random

from fmc_meta import (
    Step,
    EOStrategy,
    DRStrategy,
    FinishStrategy,
    Meta,
    nissy,
)


class GeneralEO(EOStrategy):
    def __init__(
        self,
        max_eo_length: int = 5,
        max_attempts: int = 30,
        check_inverse: bool = True,
        max_niss_split: int = 1,
    ):
        self.max_eo_length = max_eo_length
        self.max_eo_attempts = max_attempts
        self.check_inverse = check_inverse
        self.max_niss_split = max_niss_split
        self.rand = random.Random()

    @property
    def description(self) -> str:
        s = ""
        s += f"Find all EOs up to {self.max_eo_length} moves\n"
        if self.check_inverse:
            s += "Check normal and inverse\n"
            if self.max_niss_split == 0:
                s += "Don't NISS in the middle\n"
            else:
                s += f"Maximum NISS split: {self.max_niss_split}\n"
        s += f"Keep the {self.max_eo_attempts} shortest EOs\n"
        s += "Prefer non-NISS\n"
        return s

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
        elif self.check_inverse:
            all_eos.extend(eos)
            i_eos = nissy(axis_step, scramble.on_inverse(), *args)
            i_eos = [
                Step(name=s.name, previous=s.previous, moves_on_inverse=s.moves)
                for s in i_eos
            ]
            all_eos.extend(i_eos)
        all_eos.extend(eos)
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
        eos = eos[: self.max_eo_attempts]
        return eos


class OptimalDR(DRStrategy):
    def __init__(
        self,
        max_dr_length: int = 12,
        max_attempts: int = 10,
        check_inverse=True,
        max_niss_split=0,
    ):
        self.max_dr_length = max_dr_length
        self.max_dr_attempts = max_attempts
        self.check_inverse = check_inverse
        self.max_niss_split = max_niss_split
        self.eo_to_dr_stages = {
            "eofb": ["drud-eofb", "drrl-eofb"],
            "eorl": ["drud-eorl", "drfb-eorl"],
            "eoud": ["drfb-eoud", "drrl-eoud"],
        }
        self.rand = random.Random()

    @property
    def description(self) -> str:
        s = ""
        s += f"Find all DRs up to {self.max_dr_length} moves, including the preceding EO\n"
        s += "Don't break EO.\n"
        if self.check_inverse:
            s += "Check normal and inverse\n"
        if self.max_niss_split == 0:
            s += "Don't NISS in the middle\n"
        else:
            s += f"Maximum NISS split: {self.max_niss_split}"
        s += f"Keep the {self.max_dr_attempts} shortest DRs\n"
        s += "Prefer non-NISS"
        return s

    def find_drs_for_eo(self, eo: Step) -> List[Step]:
        budget = self.max_dr_length - eo.cumulative_move_count
        all_drs = []
        for next_step in self.eo_to_dr_stages[eo.name]:
            args = ["-M", budget]

            if self.check_inverse and self.max_niss_split > 0:
                args.append("-N")
            drs = nissy(next_step, eo, *args)
            if self.check_inverse and self.max_niss_split > 0:
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
                i_drs = [
                    Step(name=s.name, previous=eo, moves_on_inverse=s.moves)
                    for s in i_drs
                ]
                all_drs.extend(i_drs)

        return all_drs

    def sort_order(self, step: Step) -> Tuple:
        return (
            step.cumulative_move_count,
            step.includes_niss,
            step.requires_niss,
            self.rand.uniform(0, 1),
        )

    def select_drs(self, drs: List[Step]) -> List[Step]:
        drs.sort(key=self.sort_order)
        drs = drs[: self.max_dr_attempts]
        return drs


class SingleAxisDR(OptimalDR):
    def __init__(
        self, max_dr_length: int = 12, max_attempts: int = 10, check_inverse=True
    ):
        super().__init__(
            max_dr_length=max_dr_length,
            max_attempts=max_attempts,
            check_inverse=check_inverse,
            max_niss_split=0,
        )

    @property
    def description(self) -> str:
        s = ""
        s += f"Find all DRs up to {self.max_dr_length} moves, including the preceding EO\n"
        s += "Only consider DRs that use DR moves from a single axis\n"
        s += "Don't break EO.\n"
        if self.check_inverse:
            s += "Check normal and inverse\n"
            s += "Don't NISS in the middle\n"
        s += f"Keep the {self.max_dr_attempts} shortest DRs\n"
        s += "Prefer non-NISS"
        return s

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

        drs = list(filter(is_findable, drs))[: self.max_dr_attempts]
        return drs


class OptimalDRFinish(FinishStrategy):
    @property
    def description(self) -> str:
        s = ""
        s += f"Find the optimal DR solution that doesn't break DR"
        return s

    def dr_to_finish(self, dr: Step) -> List[Step]:
        finish_step = f"{dr.name.split('-')[0]}fin"
        return nissy(finish_step, dr)[:1]


class EasyCornerDRFinish(FinishStrategy):
    def __init__(self, max_qt_count: int = 3, max_length: int = 14):
        self.max_qt_count = max_qt_count
        self.max_length = max_length

    @property
    def description(self) -> str:
        s = ""
        s += f"Find the optimal DR solution that doesn't break DR\n"
        s += "Give up unless DR is 3QT or less"
        return s

    def dr_to_finish(self, dr: Step) -> List[Step]:
        finish_step = f"{dr.name.split('-')[0]}fin"
        finishes = nissy(finish_step, dr, "-M", self.max_length)

        def qt_count(step: Step) -> int:
            return sum(1 for m in step.moves if not "2" in m)

        return [f for f in finishes if qt_count(f) <= self.max_qt_count][:1]


available_metas = {
    "near-optimal": Meta(
        eo_strategy=GeneralEO(),
        dr_strategy=OptimalDR(),
        finish_strategy=OptimalDRFinish(),
    ),
    "single-axis-dr": Meta(
        eo_strategy=GeneralEO(),
        dr_strategy=SingleAxisDR(),
        finish_strategy=OptimalDRFinish(),
    ),
    "debug": Meta(
        eo_strategy=GeneralEO(max_eo_length=1, max_attempts=10),
        dr_strategy=OptimalDR(max_dr_length=2, max_attempts=10),
        finish_strategy=OptimalDRFinish(),
    ),
    "easy-corners": Meta(
        eo_strategy=GeneralEO(),
        dr_strategy=OptimalDR(),
        finish_strategy=EasyCornerDRFinish(),
    ),
}
