from typing import List, Tuple, Optional, Dict
import multiprocessing
from os import path
import re
import subprocess
import json

from pyhocon import ConfigFactory, ConfigTree  # type: ignore
from pydantic import BaseModel
import click

import fmc_meta
from fmc_meta import Step, Meta, MoveCountHistogram, strategies

config = ConfigFactory.parse_file(path.join(path.dirname(__file__), "meta.conf"))


class SolutionSet(BaseModel):
    scramble: Step
    eos: List[Step]
    drs: List[Step]
    finishes: List[Step]


def attempt(
    meta: Meta,
    scramble_moves: List[str],
) -> SolutionSet:
    if fmc_meta._pool is None:
        fmc_meta._pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())

    solutions = SolutionSet(
        scramble=Step(name="scramble", moves=scramble_moves),
        eos=[],
        drs=[],
        finishes=[],
    )

    print("Looking for EOs")
    solutions.eos = meta.eo.find_eos(solutions.scramble)

    print(
        f"Looking for DRs on {len(solutions.eos)} EOs: {MoveCountHistogram(steps=solutions.eos)}"
    )
    solutions.drs = meta.dr.find_drs(solutions.eos)
    print(
        f"Looking for finishes on {len(solutions.drs)} DRs: {MoveCountHistogram(steps=solutions.drs)}"
    )
    solutions.finishes = meta.finish.drs_to_finishes(solutions.drs)
    return solutions


@click.group()
def run():
    pass


@run.command(help="List pre-configured metas")
def list():
    print("Available metas:\n")
    for name, _ in config["options"].items():
        meta = load_meta(name)
        print(f"{name}:")
        print(f"  EO: {meta.eo.description()}")
        print(f"  DR: {meta.dr.description()}")
        print(f"  Finish: {meta.finish.description()}")


@run.command(help="Show command-line options for pre-configured meta")
@click.argument("meta")
def show_options(meta):
    m = load_meta(meta)
    print(f"Config options for {meta}:")
    for name, field in m.eo.model_fields.items():
        print(f"  --eo.{name}={field.default}\n    {field.description or ''}")
    print("")
    for name, field in m.dr.model_fields.items():
        print(f"  --dr.{name}={field.default}\n    {field.description or ''}")
    print("")
    for name, field in m.finish.model_fields.items():
        print(f"  --finish.{name}={field.default}\n    {field.description or ''}")


def parse_overrides(ctx):
    overrides = {}
    for arg in ctx.args:
        match = re.match("--([^=]*)=(.*)", arg)
        if match:
            overrides[match.group(1)] = match.group(2)
    return overrides


@run.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ),
    help="Dump configuration for a meta",
)
@click.argument("meta")
@click.pass_context
def dump(ctx, meta):
    the_meta = load_meta(meta, parse_overrides(ctx))
    dump = {
        "eo": the_meta.eo.model_dump() | {"class": the_meta.eo.__class__.__name__},
        "dr": the_meta.dr.model_dump() | {"class": the_meta.dr.__class__.__name__},
        "finish": the_meta.finish.model_dump()
        | {"class": the_meta.finish.__class__.__name__},
    }
    print(json.dumps(dump, indent=2))


@run.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ),
    help="Solve a scramble using the specified meta",
)
@click.option("--meta", required=True, help="Meta strategy name")
@click.option("--top", type=int, default=3, help="Show this many solutions")
@click.pass_context
def solve(ctx, meta, top):
    the_meta = load_meta(meta, parse_overrides(ctx))
    scramble = next((a for a in ctx.args if not a.startswith("--")), None)
    if not scramble:
        print("Missing scramble")
        exit(1)

    print(f"Using meta={meta}")
    print(f"Scramble: {scramble}")
    solution_set = attempt(
        meta=the_meta,
        scramble_moves=scramble.split(" "),
    )
    for sol in solution_set.finishes[:top]:
        print("")
        for step in sol.from_beginning():
            print(f"{step} // {step.name} ({step.cumulative_move_count})")


@run.command(help="Compare two metas on a set of random scrambles")
@click.option("--n", help="Number of scrambles to compare", type=int)
@click.option(
    "--report", help="File to contain the comparison report (Markdown format)"
)
@click.argument("meta1", nargs=1)
@click.argument("meta2", nargs=1)
def compare(n: int, report, meta1, meta2):
    if meta1 not in config["options"]:
        print(f"No meta named '{meta1}'")
        exit(1)
    if meta2 not in config["options"]:
        print(f"No meta named '{meta2}'")
        exit(1)
    m1 = load_meta(meta1)
    m2 = load_meta(meta2)

    with open(report, "w") as report:
        report.write(
            f"|scramble|{meta1} result|{meta2} result|winner|tie-break winner|\n"
        )
        report.write(f"|---|---|---|---|---|\n")
        for i in range(0, n):
            output = subprocess.check_output(
                ["nissy", "scramble"], encoding="UTF8"
            ).strip()
            report.write(f"|{output}")
            scramble_moves = output.split(" ")
            solutions1 = attempt(m1, scramble_moves)
            scores1 = [f.cumulative_move_count for f in solutions1.finishes[:3]]
            scores1_str = "/".join(str(s) for s in scores1)
            print(f"{meta1} found solutions in {scores1_str}")
            report.write(f"|{scores1_str}")
            solutions2 = attempt(m2, scramble_moves)
            scores2 = [f.cumulative_move_count for f in solutions2.finishes[:3]]
            scores2_str = "/".join((str(s) for s in scores2))
            print(f"{meta2} found solutions in {scores2_str}")
            report.write(f"|{scores2_str}")
            winner = ""
            if scores1 and (not scores2 or scores1[0] < scores2[0]):
                winner = meta1
            elif scores2 and (not scores1 or scores2[0] < scores1[0]):
                winner = meta2
            tie_break_winner = ""
            if not winner and scores1 and scores2:
                if tuple(scores1) < tuple(scores2):
                    tie_break_winner = meta1
                elif tuple(scores2) < tuple(scores1):
                    tie_break_winner = meta2

            report.write(f"|{winner or '-'}|{tie_break_winner or '-'}|\n")
            report.flush()


def load_meta(name: str, overrides: Optional[Dict] = None) -> "Meta":
    if path.exists(name):
        meta_cfg = ConfigFactory.parse_file(name)
    elif name in config["options"]:
        meta_cfg = config["options"][name]
    else:
        print(f"No meta named '{name}'")
        exit(1)
    if overrides:
        meta_cfg = ConfigFactory.from_dict(overrides).with_fallback(meta_cfg)
    eo = getattr(strategies, meta_cfg["eo"]["class"])(**meta_cfg["eo"])
    dr = getattr(strategies, meta_cfg["dr"]["class"])(**meta_cfg["dr"])
    finish = getattr(strategies, meta_cfg["finish"]["class"])(**meta_cfg["finish"])
    return Meta(eo=eo, dr=dr, finish=finish)


if __name__ == "__main__":
    run()
