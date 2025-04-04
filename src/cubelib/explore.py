from typing import Optional, Tuple
import io
import threading
import sys
import traceback
import logging
import math
import curses
import inspect

import cubelib.solution_builder
from cubelib.solution_builder import SolutionBuilder


def _current() -> SolutionBuilder:
    return cubelib.solution_builder._current


logging.basicConfig(
    filename="fmc-meta.log", filemode="w",
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)

from cubelib.viz import CubeViz
import cubelib.solution_builder
from py_cubelib import debug, scramble as gen_scramble, StepInfo

viz = CubeViz()
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
    ("fr", "ud"): [("slice", "ud")],
    ("fr", "fb"): [("slice", "fb")],
    ("fr", "rl"): [("slice", "rl")],
}

PREFERRED_AXIS = {
    ("eo", "ud"): (["fb","rl"], ["ud"]),
    ("eo", "rl"): (["ud","fb"], ["rl"]),
    ("eo", "fb"): (["ud","rl"], ["fb"]),
    ("*", "ud"): (["ud"], ["fb","rl"]),
    ("*", "fb"): (["fb"], ["ud","rl"]),
    ("*", "rl"): (["rl"], ["fb","ud"]),
    ("*", "*"): (["ud"], ["fb","rl"]),
}

AXIS_ORIENTATIONS = {
    ("ud", "fb"): (0, 0, 0),
    ("ud", "rl"): (0, 0, -math.pi / 2),
    ("fb", "ud"): (math.pi / 2, 0, 0),
    ("fb", "rl"): (math.pi / 2, 0, -math.pi / 2),
    ("rl", "fb"): (0, -math.pi / 2, 0),
    ("rl", "ud"): (0, -math.pi / 2, math.pi / 2),
}

_running = True


def scramble(str: Optional[str] = None):
    """Reset the cube to the given scramble"""
    if str is None:
        str = gen_scramble()
    print(str)
    viz.set_scramble(str)
    _current().clear()


def check(i=0):
    """Load and check the numbered algorithm"""
    _current().load(i - 1)
    key = (_current().kind, _current().variant)
    next_steps = NEXT_STEPS.get(key)
    if next_steps:
        _current().advance_to(*next_steps[0])


def back():
    """Go back to the previous step"""
    _current().back()


def solve():
    """Find and save solutions for the current step"""
    curr = _current()
    on_inverse = _inverse
    if on_inverse:
        niss()
    n_existing = len(curr.saved_solutions_of_same_step())
    if curr.alg.len() == 0:
        # Multiple solutions of the full step, auto-save
        algs = curr.step_info.solve(viz.cube, n_existing + 10)
        logging.debug(f"Found {len(algs)} solutions. Saving")
        count = 0
        for alg in algs:
            count += 1 if curr.save_solution(alg) else 0
            if count >= 10:
                break
        list()
    else:
        algs = curr.step_info.solve(viz.cube, n_existing + 1)
        if algs:
            existing = {f"{a}" for a in curr.saved_solutions_of_same_step()}
            for a in algs:
                if f"{a}" not in existing:
                    curr.alg = curr.alg.merge(a)
                    cubelib.solution_builder.update(curr)
                    break
        else:
            print("No solution found!")
    if on_inverse:
        niss()


def reset():
    """Reset the cube to the beginning of the current step"""
    _current().reset()


def save():
    """Save this algorithm and start a new one"""
    curr = _current()
    if not curr.step_info.is_solved(viz.cube):
        if curr.kind == "" or curr.previous is None:
            print("Complete at least one step before saving")
            return
        partial = SolutionBuilder(
            kind=curr.previous.kind,
            variant=curr.previous.variant,
            previous=curr.previous.previous,
        )
        partial.alg = curr.previous.alg.merge(curr.alg)
        options = NEXT_STEPS[(partial.kind, partial.variant)]
        case = curr.step_info.case_name(viz.cube)
        partial.comment = f"{curr.kind}{curr.variant}-{case}" if len(options) > 1 else case
        partial.save()
        return
    curr.save()
    next_steps = NEXT_STEPS.get((curr.kind, curr.variant))
    if next_steps is not None and len(next_steps) == 1:
        curr.advance_to(*next_steps[0])
    else:
        reset()


def mark(comment: str):
    """Add a comment to the current step solution"""
    if _current().step_info.is_solved(viz.cube):
        _current().comment = comment
    elif _current().previous:
        _current().previous.comment = comment


def list():
    """List the saved algorithms for the current step"""
    print(f"{_current().kind}{_current().variant}: ")
    for (i, b) in enumerate(_current().saved_solutions_of_same_step()):
        steps = b.substeps()
        summary = "\n      ".join(
            [f"{s.alg} // {s.kind} ({s.full_alg().len()}) {s.comment}" for s in steps])
        print(f" {' ' if b.is_checked else '?'}{i + 1:02d}: {summary}")


def niss():
    """Switch between normal and inverse scramble"""
    global _inverse
    _inverse = not _inverse
    viz.set_inverse(_inverse)
    viz.update()


def _append_moves(moves):
    moves = moves.split(" ")
    if _current().alg.len() > 0:
        if not _current().append_moves(moves, _inverse):
            print(
                f"{moves} not allowed after {_current().previous.kind}{_current().previous.variant}")
    else:
        if not _current().append_moves(moves, _inverse):
            assert _current().previous is not None
            if all(_current().previous.allows_move(m) for m in moves):
                alg = _current().previous.alg
                _current().back()
                _current().append_moves(alg.normal_moves(), False)
                _current().append_moves(alg.inverse_moves(), True)
                _current().append_moves(moves, _inverse)
            else:
                print(
                    f"{moves} not allowed after {_current().previous.kind}{_current().previous.variant}")


def _get_preferred_axis(kind, variant) -> Tuple[str, str]:
    # top/bottom axis and front/back axis
    axis = PREFERRED_AXIS.get(
        (kind, variant),
        PREFERRED_AXIS.get(("*", variant),
                           PREFERRED_AXIS.get(("*", "*"))),
    )
    return axis


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
    _set_mode("eo", "fb")


def eorl():
    """Look for EO on RL axis"""
    _set_mode("eo", "rl")


def eoud():
    """Look for EO on UD axis"""
    _set_mode("eo", "ud")


def drud():
    """Look for DR on UD axis"""
    _set_mode("dr", "ud")


def drrl():
    """Look for DR on RL axis"""
    _set_mode("dr", "rl")


def drfb():
    """Look for DR on FB axis"""
    _set_mode("dr", "fb")


def htr():
    """Look for HTR"""
    _set_mode("htr", _current().previous.variant)


def fr():
    """Look for FR"""
    _set_mode("fr", _current().previous.variant)


def _set_mode(kind, variant) -> bool:
    step_info = StepInfo(kind, variant)
    if step_info.is_eligible(viz.cube):
        if (not _current().alg.is_empty()) and not _current().step_info.is_solved(viz.cube):
            reset()
        _current().advance_to(kind, variant)
        while step_info.is_solved(viz.cube) and _current().previous:
            _current().back()
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
        s = f"{_current().kind}{_current().variant}> {cmd}"
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
    print(f"{_current().full_alg()}")


def _update(old_builder, new_builder):
    if (old_builder.kind, old_builder.variant) != (new_builder.kind, new_builder.variant):
        old_top, old_front = _get_preferred_axis(old_builder.kind, old_builder.variant)
        new_top, new_front = _get_preferred_axis(new_builder.kind, new_builder.variant)
        if len(new_top) > 1:
            new_top = [f for f in old_top if f in new_top]
        if len(new_front) > 1:
            new_front = [f for f in old_front if f in new_front]
        _set_orientation(*AXIS_ORIENTATIONS[(new_top[0], new_front[0])])
    viz.update()


if __name__ == "__main__":
    cubelib.solution_builder._listener = _update
    viz.update()
    threading.Thread(target=lambda: curses.wrapper(read_commands)).start()
    scramble()
    eorl()
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
