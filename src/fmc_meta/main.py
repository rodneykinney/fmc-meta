from typing import List, Tuple, Optional, Dict
import sys
from dataclasses import dataclass
import multiprocessing
import argparse
from os import path
import re

from pyhocon import ConfigFactory, ConfigTree  # type: ignore
import click

import fmc_meta
from fmc_meta import Step, Meta, MoveCountHistogram, strategies

config = ConfigFactory.parse_file(
    path.join(path.dirname(strategies.__file__), "meta.conf")
)


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


@click.group()
def run():
    pass


@run.command()
def list():
    print("Available metas:\n")
    for key, cfg in config["options"].items():
        print(f"{key}:\n  {cfg['description']}")


@run.command()
@click.argument("meta")
def show_options(meta):
    if meta not in config["options"]:
        print(f"No meta named '{meta}'")
        exit(1)
    m = load_meta(config["options"][meta])
    print(f"Config options for {meta}:")
    for name, field in m.eo_strategy.model_fields.items():
        print(f"  --eo.{name}={field.default}\n    {field.description or ''}")
    print("")
    for name, field in m.dr_strategy.model_fields.items():
        print(f"  --dr.{name}={field.default}\n    {field.description or ''}")
    print("")
    for name, field in m.finish_strategy.model_fields.items():
        print(f"  --finish.{name}={field.default}\n    {field.description or ''}")


@run.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.option("--meta", required=True, help="Meta strategy name")
@click.argument("scramble")
@click.pass_context
def solve(ctx, meta, scramble):
    if meta not in config["options"]:
        print(f"No meta named '{meta}'")
        exit(1)

    overrides = {}
    for arg in ctx.args:
        match = re.match("--([^=]*)=(.*)", arg)
        if match:
            overrides[match.group(1)] = match.group(2)
    the_meta = load_meta(config["options"][meta], overrides)

    print(f"Using meta={meta}")
    print(f"Scramble: {scramble}")
    fmc_meta._pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    solution_set = attempt(
        meta=the_meta,
        scramble_moves=scramble.split(" "),
    )
    print("")
    print(solution_set.summary(4))


def load_meta(config: ConfigTree, overrides: Optional[Dict] = None) -> Meta:
    if overrides:
        config = ConfigFactory.from_dict(overrides).with_fallback(config)
    eo = getattr(strategies, config["eo"]["class"])(**config["eo"])
    dr = getattr(strategies, config["dr"]["class"])(**config["dr"])
    finish = getattr(strategies, config["finish"]["class"])(**config["finish"])
    return Meta(eo_strategy=eo, dr_strategy=dr, finish_strategy=finish)


if __name__ == "__main__":
    run()
