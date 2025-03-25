from typing import Optional
import io
import threading
import sys
import traceback
import logging
import math
import curses
from builtins import (list as llist)
import inspect

logging.basicConfig(
    filename="fmc-meta.log", filemode="w",
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)

from cubelib.viz import CubeViz
import cubelib.solution_builder
from py_cubelib import debug, scramble as gen_scramble, StepInfo

viz = CubeViz()
_builder = cubelib.solution_builder._builder
_inverse = False

NEXT_STEPS = {
    ("eo", "ud"): [("dr", "fb"), ("dr", "rl")],
    ("eo", "rl"): [("dr", "ud"), ("dr", "fb")],
    ("eo", "fb"): [("dr", "ud"), ("dr", "rl")],
    ("dr", "ud"): [("htr", "ud")],
    ("dr", "rl"): [("htr", "rl")],
    ("dr", "fb"): [("htr", "fb")],
    ("htr", "ud"): [("fr", "ud")],
    ("htr", "rl"): [("fr", "rl")],
    ("htr", "fb"): [("fr", "fb")],
    ("fr", "ud"): [("slice", "")],
    ("fr", "fr"): [("slice", "")],
    ("fr", "rl"): [("slice", "")],
}

_running = True


def scramble(str: Optional[str] = None):
    """Reset the cube to the given scramble"""
    if str is None:
        str = gen_scramble()
    print(str)
    viz.set_scramble(str)
    _builder.clear()


def check(i=0):
    """Load and check the numbered algorithm"""
    _builder.load(i - 1)
    key = (_builder.kind, _builder.variant)
    next_steps = NEXT_STEPS.get(key)
    if next_steps:
        _builder.advance_to(*next_steps[0])


def back():
    """Go back to the previous step"""
    _builder.back()


def solve(max: int = 0):
    """Find and save solutions for the current step"""
    algs = _builder.step_info.solve(viz.cube, max)
    count = 0
    for alg in algs:
        count += 1 if _builder.save_solution(alg) else 0
        if count >= 10:
            break
    list()


def reset():
    """Reset the cube to the beginning of the current step"""
    _builder.reset()
    if _inverse:
        niss()


def save():
    """Save this algorithm and start a new one"""
    if not _builder.step_info.is_solved(viz.cube):
        print(f"Cube is not in {_builder.kind}{_builder.variant}")
        return
    _builder.save()
    next_steps = NEXT_STEPS.get((_builder.kind, _builder.variant))
    if next_steps is not None and len(next_steps) == 1:
        _builder.advance_to(*next_steps[0])
    else:
        reset()


def mark(comment: str):
    """Add a comment to the current step solution"""
    if _builder.step_info.is_solved(viz.cube):
        _builder.comment = comment
    elif _builder.previous:
        _builder.previous.comment = comment

def list():
    """List the saved algorithms for the current step"""
    print(f"{_builder.kind}{_builder.variant}: ")
    for (i, b) in enumerate(_builder.saved_solutions_of_same_step()):
        full_alg = b.full_alg()
        comment = f" // {b.comment}" if b.comment else ""
        print(f" {' ' if b.is_checked else '?'}{i + 1}: {full_alg} ({full_alg.len()}){comment}")


def niss():
    """Switch between normal and inverse scramble"""
    global _inverse
    _inverse = not _inverse
    viz.set_inverse(_inverse)
    viz.update(_builder)


def _append_moves(moves):
    if not _builder.append_moves(moves.split(" "), _inverse):
        print(f"{moves} not allowed after {_builder.previous.kind}{_builder.previous.variant}")


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
    _set_orientation(0, 0, 0)
    _set_mode("eo", "fb")


def eorl():
    _set_orientation(0, 0, -math.pi / 2)
    """Look for EO on RL axis"""
    _set_mode("eo", "rl")


def eoud():
    _set_orientation(math.pi / 2, 0, 0)
    """Look for EO on UD axis"""
    _set_mode("eo", "ud")


def drud():
    """Look for DR on UD axis"""
    if _set_mode("dr", "ud"):
        if _builder.previous.variant == "fb":
            _set_orientation(0, 0, 0)
        else:
            _set_orientation(0, -math.pi / 2, 0)


def drrl():
    """Look for DR on RL axis"""
    if _set_mode("dr", "rl"):
        if _builder.previous.variant == "fb":
            _set_orientation(0, -math.pi / 2, 0)
        else:
            _set_orientation(0, -math.pi / 2, math.pi / 2)


def drfb():
    """Look for DR on FB axis"""
    if _set_mode("dr", "fb"):
        if _builder.previous.variant == "ud":
            _set_orientation(math.pi / 2, 0, 0)
        else:
            _set_orientation(math.pi / 2, 0, math.pi / 2)


def htr():
    """Look for HTR"""
    _set_mode("htr", _builder.previous.variant)


def fr():
    """Look for FR"""
    _set_mode("fr", _builder.previous.variant)


def _set_mode(kind, variant) -> bool:
    step_info = StepInfo(kind, variant)
    if step_info.is_eligible(viz.cube):
        if (not _builder.alg.is_empty()) and not _builder.step_info.is_solved(viz.cube):
            reset()
        _builder.advance_to(kind, variant)
        while step_info.is_solved(viz.cube) and _builder.previous:
            _builder.back()
        return True
    else:
        print(f"Cube is not eligible for {kind}{variant}")
        return False


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

    def flush():
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
                flush()
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
                flush()
                cmd = last_command
                prompt()
            elif chr(key) in {'x', 'y', 'z'} and cmd == "":
                exec(f"_{chr(key)}()")
            else:
                cmd += chr(key)
                prompt()
        except NameError:
            print(f'Unknown command "{cmd}". Type "help" for help')
            flush()
            cmd = ""
            prompt()
        except Exception as e:
            try:
                logging.debug(traceback.format_exc())
                logging.debug(sys.exc_info())
                print(f"Error: {e}")
                flush()
                cmd = ""
                prompt()
            except:
                pass


def _debug():
    print(f"{_builder.full_alg()}")


def update(builder):
    global _builder
    _builder = builder
    viz.update(builder)


if __name__ == "__main__":
    _builder.listener = update
    viz.update(_builder)
    threading.Thread(target=lambda: curses.wrapper(read_commands)).start()
    # scramble()
    # eofb()
    # solve(max=4)
    # check(1)
    # drud()

    # scramble("U L' B' U2 R2 B2 D R L F' R2 D2 B2 R2 U2 F2 D' R2 U' L2 U B2 U2")
    # eofb()
    # niss(); _append_moves("B") ; niss() ;_append_moves("F' L' F") ; save() ; check()
    # niss(); _append_moves("F2 R"); niss() ; _append_moves("R2 L2 D U2 L") ; save()
    # _append_moves("R2 F2 D' B2 U2 R2 U R2 U") ; save()
    # niss(); _append_moves("B F L F") ; niss() ; save()
    # _append_moves("f") ; niss() ; _append_moves("D2 L B") ; niss() ; save()
    # niss(); _append_moves("B") ; niss() ;_append_moves("U2 B L B") ; save()
    # niss(); _append_moves("B") ; niss() ;_append_moves("D2 F R F") ; save()

    # eofb()
    # _append_moves("F' U2 R L B")
    # drrl()
    # _append_moves("U' L' D2 F2 R' D' R2 D")
    # save()
    # _append_moves("R' F2 B2 D2 R B2 R")
    # save()

    # drfb()
    # save()
    # check()
    # htr()
    # _append_moves("B R2 L2 U2 R2 F' R2 F")
    # save()
    # check()
    # fr()

    viz.run()
