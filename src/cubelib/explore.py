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

_mode = ""
_running = True
# Nested dict of (kind,variant) => list of (alg, dict) pairs
_steps = defaultdict(llist)
# Pointer to the steps leading up to the one being worked on
_selector = []
# Algorithm currently being built by the user
_kind, _variant = "", ""
_alg_steps = []


def build_solution() -> Solution:
    sol = Solution()
    next_step_options = _steps
    for ((kind, variant), pos) in _selector:
        if pos is not None:
            alg, d = next_step_options[(kind, variant)][pos]
            sol.append(SolutionStep(kind=kind, variant=variant, alg=alg, comment=""))
            next_step_options = d
    sol.append(
        SolutionStep(kind=_kind, variant=_variant, alg=" ".join(_alg_steps), comment=""))
    return sol


def scramble(str=""):
    viz.set_scramble(str)
    set_mode("", "")
    reset()


def check(i):
    _alg_steps.clear()
    _selector.append(((_kind, _variant), i - 1))
    set_mode("", "")


def reset():
    _alg_steps.clear()
    _kind, _variant = "",""
    viz.set_solution(build_solution())


def save():
    next_step_options = _steps
    for ((kind, variant), pos) in _selector:
        _, next_step_options = next_step_options[(kind, variant)][pos]
    next_step_options[(_kind, _variant)].append((" ".join(_alg_steps), defaultdict(llist)))
    _alg_steps.clear()
    viz.set_solution(build_solution())


def list():
    next_step_options = _steps
    for ((kind, variant), pos) in _selector:
        if pos is not None:
            _, next_step_options = next_step_options[(kind, variant)][pos]
    print(f"{_kind}{_variant}:")
    for (i, (alg, _)) in enumerate(next_step_options[(_kind, _variant)]):
        print(f"  {i + 1}: {alg}")


def _append_move(move):
    if _alg_steps and _alg_steps[-1][0] == move[0]:
        suffixes = {_alg_steps[-1][1:], move[1:]}
        if suffixes == {"", ""} or suffixes == {"'", "'"}:
            _alg_steps[-1] = f"{move[0]}2"
        elif suffixes == {"'", ""} or suffixes == {"2", "2"}:
            _alg_steps.pop()
        elif suffixes == {"", "2"}:
            _alg_steps[-1] = f"{move[0][0]}'"
        elif suffixes == {"'", "2"}:
            _alg_steps[-1] = move[0][:1]
        else:
            raise ValueError(f"Could not combine {move} with {_alg_steps[-1]}")
    else:
        _alg_steps.append(move)
    viz.set_solution(build_solution())


def eofb():
    set_mode("eo", "fb")


def eorl():
    set_mode("eo", "rl")


def eoud():
    set_mode("eo", "ud")


def drud():
    set_mode("dr", "ud")


def set_mode(step, variant):
    _alg_steps.clear()
    global _kind, _variant
    _kind, _variant = step, variant
    viz.set_solution(build_solution())


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
            cmd = input(f"{_mode}> ").strip()
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
