from typing import List, Tuple
import sys
from dataclasses import dataclass
import multiprocessing
import argparse

import fmc_meta
from fmc_meta import Step, Meta, MoveCountHistogram, strategies


@dataclass
class SolutionSet:
    scramble: Step
    eos: List[Step]
    drs: List[Step]
    finishes: List[Step]

    def solution_summary(self, sol: Step) -> str:
        s = ""
        for step in sol.from_beginning():
            s += f"{step} // {step.name} ({step.cumulative_move_count})\n"
        return s

    def summary(self, solution_count: int = 3) -> str:
        s = ""
        for sol in self.finishes[:solution_count]:
            s += f"{self.solution_summary(sol)}\n"
        return s


def attempt(
    meta: Meta,
    scramble_moves: List[str],
) -> SolutionSet:
    solutions = SolutionSet(
        scramble=Step(name="scramble", moves=scramble_moves),
        eos=[],
        drs=[],
        finishes=[],
    )

    print("Looking for EOs")
    solutions.eos = meta.eo_strategy.find_eos(solutions.scramble)

    print(
        f"Looking for DRs on {len(solutions.eos)} EOs: {MoveCountHistogram(solutions.eos)}"
    )
    solutions.drs = meta.dr_strategy.find_drs(solutions.eos)
    print(
        f"Looking for finishes on {len(solutions.drs)} DRs: {MoveCountHistogram(solutions.drs)}"
    )
    solutions.finishes = meta.finish_strategy.drs_to_finishes(solutions.drs)
    return solutions


def run():
    parser = argparse.ArgumentParser(prog="fmc-meta")
    parser.add_argument("-m", "--meta")
    parser.add_argument(
        "-l", "--list", action="store_true", help="List available metas"
    )
    parser.add_argument("-s", "--show", action="store_true", help="Describe named meta")
    parser.add_argument("scramble", nargs="?")
    args = parser.parse_args()
    if args.list:
        print("Available metas:")
        for name, meta in strategies.available_metas.items():
            print(f"  {name}")
        sys.exit(0)
    if args.meta not in strategies.available_metas:
        print(f"Unknown meta: {args.meta}")
        sys.exit(1)
    meta = strategies.available_metas[args.meta]
    if args.show:
        print(f"Behavior of --meta {args.meta}:\n")
        print(meta.description)
        exit(0)
    if not args.scramble:
        print("Missing scramble")
        parser.print_help()
        exit(1)
    scramble = args.scramble
    fmc_meta._pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    print(f"Using meta={args.meta}")
    print(f"Scramble: {scramble}")
    solution_set = attempt(
        meta=meta,
        scramble_moves=scramble.split(" "),
    )
    print("")
    print(solution_set.summary())


if __name__ == "__main__":
    run()
