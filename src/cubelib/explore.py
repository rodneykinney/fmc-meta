from typing import Optional, Dict, List, Tuple
import io
import threading
import sys
import traceback
import logging
import math
import curses
from collections import defaultdict
from builtins import (list as llist)
import inspect

logging.basicConfig(
    filename="fmc-meta.log", filemode="w",
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)

from cubelib.viz import CubeViz
from py_cubelib import Solution, SolutionStep, Algorithm, StepInfo, debug

DEFAULT_NEXT_STEPS = {
    ("dr", "ud"): ("htr", "ud"),
    ("dr", "rl"): ("htr", "rl"),
    ("dr", "fb"): ("htr", "fb"),
    ("htr", "ud"): ("fr", "ud"),
    ("htr", "rl"): ("fr", "rl"),
    ("htr", "fb"): ("fr", "fb"),
}


class SolutionBuilder:
    def __init__(self, kind: str, variant: str, previous: Optional["SolutionBuilder"] = None):
        self.kind = kind
        self.variant = variant
        self.step_info = StepInfo(kind, variant)
        self.previous = previous
        self.moves = []

    def add_move(self, move: str):
        if self.moves and self.moves[-1][0] == move[0]:
            suffixes = {self.moves[-1][1:], move[1:]}
            if suffixes == {"", ""} or suffixes == {"'", "'"}:
                self.moves[-1] = f"{move[0]}2"
            elif suffixes == {"'", ""} or suffixes == {"2", "2"}:
                self.moves.pop()
            elif suffixes == {"", "2"}:
                self.moves[-1] = f"{move[0][0]}'"
            elif suffixes == {"'", "2"}:
                self.moves[-1] = move[0][:1]
            else:
                raise ValueError(f"Could not combine {move} with {self.moves[-1]}")
        else:
            self.moves.append(move)

    def allows_move(self, move: str) -> bool:
        if self.previous is None:
            return True
        return self.previous.step_info.is_move_allowed(move)

    def all_moves(self):
        if self.previous is not None:
            return self.previous.all_moves() + self.moves
        return self.moves

    def build(self) -> Solution:
        sol = Solution()
        if self.previous is not None:
            sol = self.previous.build()
        sol.append(SolutionStep(kind=self.kind, variant=self.variant, alg=" ".join(self.moves),
                                comment=""))
        return sol


_running = True
# Nested dict of (kind,variant) => SolutionBuilder
_steps: Dict[Tuple[str, str], List[SolutionBuilder]] = defaultdict(llist)
# The algorithm currently being built
_builder = SolutionBuilder("", "")


def scramble(str=""):
    """Reset the cube to the given scramble"""
    global _builder
    viz.set_scramble(str)
    _builder = SolutionBuilder("", "")
    viz.set_solution(_builder.build())


def check(i=0):
    """Load and check the numbered algorithm"""
    global _builder
    if not _steps.get((_builder.kind, _builder.variant), list()):
        return
    b = _steps[(_builder.kind, _builder.variant)][i - 1]
    kind, variant = "",""
    # next = DEFAULT_NEXT_STEPS.get((_builder.kind, _builder.variant))
    # if next is not None:
    #     kind,variant = next
    _builder = SolutionBuilder(
        kind=kind,
        variant=variant,
        previous=b
    )
    viz.set_solution(_builder.build())


def back():
    """Go back to the previous step"""
    global _builder
    prev = _builder.previous
    if prev is not None:
        _builder = SolutionBuilder(prev.kind, prev.variant, prev.previous)
        viz.set_solution(_builder.build())
    else:
        _builder = SolutionBuilder("", "")
        viz.set_solution(_builder.build())


def reset():
    """Reset the cube to the beginning of the current step"""
    global _builder
    _builder = SolutionBuilder(_builder.kind, _builder.variant, previous=_builder.previous)
    viz.set_solution(_builder.build())


def save():
    """Save this algorithm and start a new one"""
    global _builder
    if _builder.step_info.is_solved(viz.cube):
        _steps[(_builder.kind, _builder.variant)].append(_builder)
        _builder = SolutionBuilder(_builder.kind, _builder.variant, previous=_builder.previous)
        viz.set_solution(_builder.build())
        reset()
        # if (_builder.kind, _builder.variant) in DEFAULT_NEXT_STEPS:
        #     check()
        # else:
        #     reset()
    else:
        print(f"Cube is not in {_builder.kind}{_builder.variant}")


def list():
    """List the saved algorithms for the current step"""
    print(f"{_builder.kind.upper()}{_builder.variant.upper()}: ")
    for (i, b) in enumerate(_steps[(_builder.kind, _builder.variant)]):
        s = b.all_moves()
        print(f"  {i + 1}: {' '.join(s)} ({len(s)})")


def _append_moves(moves):
    for move in moves.split(" "):
        if _builder.allows_move(move):
            _builder.add_move(move)
            viz.set_solution(_builder.build())
        else:
            print(f"{move} not allowed after {_builder.previous.kind}{_builder.previous.variant}")


def _set_orientation(x, y, z):
    viz.xq_angle = x
    viz.yq_angle = y
    viz.zq_angle = z


def _x():
    _set_orientation(viz.xq_angle - math.pi / 2, 0, 0)


def _y():
    _set_orientation(0, 0, viz.zq_angle - math.pi / 2)


def _z():
    _set_orientation(0, viz.yq_angle + math.pi / 2, 0)


def eofb():
    """Look for EO on FB axis"""
    _set_orientation(0,0,0)
    _set_mode("eo", "fb")


def eorl():
    _set_orientation(0,0, -math.pi/2)
    """Look for EO on RL axis"""
    _set_mode("eo", "rl")


def eoud():
    _set_orientation(-math.pi/2,0,0)
    """Look for EO on UD axis"""
    _set_mode("eo", "ud")


def drud():
    _set_orientation(0,0,0)
    """Look for DR on UD axis"""
    _set_mode("dr", "ud")


def drrl():
    """Look for DR on RL axis"""
    _set_orientation(0,-math.pi/2,0)
    _set_mode("dr", "rl")


def drfb():
    """Look for DR on FB axis"""
    _set_orientation(math.pi/2,0,0)
    _set_mode("dr", "fb")


def htr():
    """Look for HTR"""
    _set_mode("htr", _builder.previous.variant)


def fr():
    """Look for FR"""
    _set_mode("fr", _builder.previous.variant)


def _set_mode(kind, variant):
    global _builder
    if _builder.step_info.is_solved(viz.cube):
        _builder.kind = kind
        _builder.variant = variant
        _builder.step_info = StepInfo(kind, variant)
        viz.set_solution(_builder.build())
    elif _builder.step_info.is_eligible(viz.cube):
        _builder = SolutionBuilder(kind, variant, previous=_builder.previous)
        viz.set_solution(_builder.build())
    else:
        print(f"Cube is not eligible for {kind}{variant}")


def help():
    """Print this help command"""
    print("Cube view: [x,y,z] to change orientation, [left,right] to rotate")
    print("Commands:")
    m = inspect.getmembers(sys.modules[__name__], inspect.isfunction)
    for (name, func) in m:
        if not name.startswith("_"):
            print(f"  {name}:")
            print(f"    {func.__doc__}")


def corners():
    """Toggle visibility of corners"""
    viz.hide_corners = not viz.hide_corners
    viz.refresh()


def edges():
    """Toggle visibility of edges"""
    viz.hide_edges = not viz.hide_edges
    viz.refresh()


def show_all():
    """Show all pieces"""
    viz.show_all = not viz.show_all
    viz.hide_corners = viz.show_all
    viz.hide_edges = viz.show_all
    viz.refresh()


def quit():
    """Exit"""
    global _running
    _running = False
    viz.stop()


MOVES = {
    "R", "U", "F", "L", "D", "B",
    "R'", "U'", "F'", "L'", "D'", "B'",
    "R2", "U2", "F2", "L2", "D2", "B2",
}

last_command = ""


def read_commands(window):
    curses.noecho()
    curses.cbreak()
    window.keypad(True)

    def execute(cmd):
        if len([m for m in cmd.upper().split(" ") if m not in MOVES]) == 0:
            _append_moves(cmd.upper())
        else:
            if cmd.find("(") < 0:
                cmd = f"{cmd}()"
            exec(cmd)

    def prompt():
        s = f"{_builder.kind}{_builder.variant}> {cmd}"
        window.move(0, 0)
        window.clrtoeol()
        window.addstr(0, 0, s)
        window.move(0, len(s))
        window.refresh()

    def dump_stdout():
        window.move(1, 0)
        window.clrtobot()
        window.addstr(1, 0, stdout_buffer.getvalue())
        stdout_buffer.truncate(0)
        stdout_buffer.seek(0)

    stdout_buffer = io.StringIO()
    sys.stdout = stdout_buffer
    sys.stderr = None

    window.clear()
    cmd = ""
    prompt()
    while _running:
        try:
            key = window.getch()
            if key == curses.KEY_ENTER or key == 10:
                execute(cmd.strip())
                dump_stdout()
                global last_command
                last_command = cmd
                cmd = ""
                prompt()
            elif key == curses.KEY_BACKSPACE or key == 127:
                cmd = cmd[:-1]
                prompt()
            elif key == curses.KEY_LEFT:
                viz.rotate(-25)
            elif key == curses.KEY_RIGHT:
                viz.rotate(25)
            elif key == curses.KEY_UP:
                dump_stdout()
                cmd = last_command
                prompt()
            elif chr(key) in {'x', 'y', 'z'} and cmd == "":
                exec(f"_{chr(key)}()")
            else:
                cmd += chr(key)
                prompt()
        except:
            try:
                logging.debug(traceback.format_exc())
                logging.debug(sys.exc_info())
                print(f'Unknown command "{cmd}". Type "help" for help')
                dump_stdout()
                cmd = ""
                prompt()
            except:
                pass


def _debug():
    print(debug(viz.cube))


viz = CubeViz()

if __name__ == "__main__":
    scramble("U L' B' U2 R2 B2 D R L F' R2 D2 B2 R2 U2 F2 D' R2 U' L2 U B2 U2")
    # eofb()
    # _append_moves("F' D2 R L F")
    # drrl()
    # _append_moves("U' L' F2 D2 R' D' L2 D")

    # save()
    # check()
    # drfb()
    # save()
    # check()
    # htr()
    # _append_moves("B R2 L2 U2 R2 F' R2 F")
    # save()
    # check()
    # fr()

    threading.Thread(target=lambda: curses.wrapper(read_commands)).start()
    viz.run()
