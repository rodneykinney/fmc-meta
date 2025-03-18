from functools import cached_property
from typing import Optional, Dict, List, Tuple
import threading
import sys
import traceback
import logging
from collections import defaultdict
from builtins import (list as llist)

logging.basicConfig(
    filename="fmc-meta.log", filemode="w",
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)

from cubelib.viz import CubeViz
from py_cubelib import Solution, SolutionStep, Algorithm


class SolutionBuilder:
    def __init__(self, kind: str, variant: str, previous: Optional["SolutionBuilder"] = None):
        self.kind = kind
        self.variant = variant
        self.previous = previous
        self.steps = []

    def add_step(self, move: str):
        if self.steps and self.steps[-1][0] == move[0]:
            suffixes = {self.steps[-1][1:], move[1:]}
            if suffixes == {"", ""} or suffixes == {"'", "'"}:
                self.steps[-1] = f"{move[0]}2"
            elif suffixes == {"'", ""} or suffixes == {"2", "2"}:
                self.steps.pop()
            elif suffixes == {"", "2"}:
                self.steps[-1] = f"{move[0][0]}'"
            elif suffixes == {"'", "2"}:
                self.steps[-1] = move[0][:1]
            else:
                raise ValueError(f"Could not combine {move} with {self.steps[-1]}")
        else:
            self.steps.append(move)

    def all_steps(self):
        if self.previous is not None:
            return self.previous.all_steps() + self.steps
        return self.steps
    
    def build(self) -> Solution:
        sol = Solution()
        if self.previous is not None:
            sol = self.previous.build()
        sol.append(SolutionStep(kind=self.kind, variant=self.variant, alg=" ".join(self.steps), comment=""))
        return sol


_running = True
# Nested dict of (kind,variant) => SolutionBuilder
_steps: Dict[Tuple[str, str], List[SolutionBuilder]] = defaultdict(llist)
# The algorithm currently being built
_builder = SolutionBuilder("", "")


def scramble(str=""):
    global _builder
    viz.set_scramble(str)
    _builder = SolutionBuilder("", "")
    viz.set_solution(_builder.build())


def check(i):
    global _builder
    b = _steps[(_builder.kind, _builder.variant)][i - 1]
    _builder = SolutionBuilder(
        kind="",
        variant="",
        previous = b  
    )
    viz.set_solution(_builder.build())

def back():
    if _builder.previous is not None:
        global _builder
        _builder = _builder.previous
        viz.set_solution(_builder.build())


def reset():
    _builder.steps.clear()
    viz.set_solution(_builder.build())


def save():
    global _builder
    _steps[(_builder.kind, _builder.variant)].append(_builder)
    _builder = SolutionBuilder(_builder.kind, _builder.variant, previous = _builder.previous)
    viz.set_solution(_builder.build())


def list():
    for (i, b) in enumerate(_steps[(_builder.kind, _builder.variant)]):
        s = b.all_steps()
        print(f"  {i + 1}: {' '.join(s)} ({len(s)})")


def _append_move(move):
    _builder.add_step(move)
    viz.set_solution(_builder.build())


def eofb():
    set_mode("eo", "fb")


def eorl():
    set_mode("eo", "rl")


def eoud():
    set_mode("eo", "ud")


def drud():
    set_mode("dr", "ud")
def drrl():
    set_mode("dr", "rl")
def drfb():
    set_mode("dr", "fb")


def set_mode(step, variant):
    global _builder
    _builder = SolutionBuilder(step, variant, previous = _builder.previous)
    viz.set_solution(_builder.build())


def help():
    print("Commands:")
    print("  scramble(str)")
    print("  list")
    print("")
    print("  eofb")
    print("  eorl")
    print("  eoud")
    print("")
    print("  quit")
    print("  help")


def quit():
    global _running
    _running = False
    viz.stop()


MOVES = {
    "R", "U", "F", "L", "D", "B",
    "R'", "U'", "F'", "L'", "D'", "B'",
    "R2", "U2", "F2", "L2", "D2", "B2",
}


def read_commands():
    cmd = ""
    while _running:
        try:
            cmd = input(f"{_builder.kind}{_builder.variant}> ").strip()
            if cmd.upper() in MOVES:
                _append_move(cmd.upper())
            else:
                if cmd.find("(") < 0:
                    cmd = f"{cmd}()"
                exec(cmd)
        except:
            logging.debug(traceback.format_exc())
            logging.debug(sys.exc_info())
            print(f'Unknown command "{cmd}". Type "help" for help')


viz = CubeViz()

if __name__ == "__main__":
    threading.Thread(target=read_commands).start()
    viz.run()
