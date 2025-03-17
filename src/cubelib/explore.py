import threading
import sys
import traceback
import logging
from collections import defaultdict

logging.basicConfig(
    filename="fmc-meta.log", filemode="w",
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)

from cubelib.viz import CubeViz
from py_cubelib import Solution, SolutionStep, Algorithm

_mode = ""
_scramble = ""
_running = True
_solution = Solution()
_all_solutions = []


def scramble(str = ""):
    global _scramble
    _scramble = str
    viz.set_scramble(str)
    _solution = Solution()
    viz.set_solution(_solution)

def check(i):
    pass

def reset():
    global _solution
    _solution = Solution()
    viz.set_solution(_solution)

def save():
    global _solution
    _all_solutions.append(_solution)
    kind, variant = _solution.steps[-1].kind, _solution.steps[-1].variant
    _solution = Solution()
    set_mode(kind, variant)

def list():
    solutions = [s for s in _all_solutions
                 if s.steps and _solution.steps
                 and s.steps[-1].kind == _solution.steps[-1].kind
                 and s.steps[-1].variant == _solution.steps[-1].variant
                 ]
    if solutions:
        print(f"{_solution.steps[-1].kind}{_solution.steps[-1].variant}")
        for i, sol in enumerate(solutions):
            print(f"{i+1}: {sol}")

def append_move(move):
    if _solution.steps:
        _solution.steps = _solution.steps[:-1] + [SolutionStep(
            kind = _solution.steps[-1].kind,
            variant = _solution.steps[-1].variant,
            alg = f"{_solution.steps[-1].alg} {move}",
            comment = _solution.steps[-1].comment
        )]
        viz.set_solution(_solution)

def eofb():
    set_mode("eo", "fb")

def eorl():
    set_mode("eo", "rl")


def eoud():
    set_mode("eo", "ud")

def drud():
    set_mode("dr", "ud")


def set_mode(step, variant):
    _solution.append(SolutionStep(step, variant, "", ""))
    viz.set_solution(_solution)


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
            cmd = input(f"{_mode}> ")
            if cmd.upper() in MOVES:
                append_move(cmd.upper())
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
