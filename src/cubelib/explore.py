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
from py_cubelib import debug, StepInfo

_builder = cubelib.solution_builder._builder

NEXT_STEPS_AFTER_SAVE = {
    ("dr", "ud"): ("htr", "ud"),
    ("dr", "rl"): ("htr", "rl"),
    ("dr", "fb"): ("htr", "fb"),
    ("htr", "ud"): ("fr", "ud"),
    ("htr", "rl"): ("fr", "rl"),
    ("htr", "fb"): ("fr", "fb"),
}

NEXT_STEPS = {
    ("eo", "ud"): ("dr", "fb"),
    ("eo", "rl"): ("dr", "ud"),
    ("eo", "fb"): ("dr", "ud"),
}




_running = True


def scramble(str=""):
    """Reset the cube to the given scramble"""
    viz.set_scramble(str)
    _builder.clear()


def check(i=0):
    """Load and check the numbered algorithm"""
    _builder.load(i)
    key = (_builder.kind, _builder.variant)
    next = NEXT_STEPS.get(key, NEXT_STEPS_AFTER_SAVE.get(key))
    if next:
        _builder.advance_to(*next)


def back():
    """Go back to the previous step"""
    _builder.back()

def reset():
    """Reset the cube to the beginning of the current step"""
    _builder.reset()


def save():
    """Save this algorithm and start a new one"""
    if _builder.step_info.is_solved(viz.cube):
        _builder.save()
        next_step =  NEXT_STEPS_AFTER_SAVE.get((_builder.kind, _builder.variant))
        if next_step:
            _builder.advance_to(*next_step)
        else:
            _builder.reset()
    else:
        print(f"Cube is not in {_builder.kind}{_builder.variant}")


def list():
    """List the saved algorithms for the current step"""
    print(f"{_builder.kind.upper()}{_builder.variant.upper()}: ")
    for (i, b) in enumerate(_builder.saved_solutions_of_same_step()):
        s = b.all_moves()
        print(f"  {i + 1}: {' '.join(s)} ({len(s)})")


def _append_moves(moves):
    if not _builder.append_moves(moves.split(" ")):
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
    _set_orientation(0,0,0)
    _set_mode("eo", "fb")



def eorl():
    _set_orientation(0,0, -math.pi/2)
    """Look for EO on RL axis"""
    _set_mode("eo", "rl")


def eoud():
    _set_orientation(math.pi/2,0,0)
    """Look for EO on UD axis"""
    _set_mode("eo", "ud")


def drud():
    """Look for DR on UD axis"""
    if _set_mode("dr", "ud"):
        _set_orientation(0,0,0)


def drrl():
    """Look for DR on RL axis"""
    if _set_mode("dr", "rl"):
        _set_orientation(0,-math.pi/2,0)


def drfb():
    """Look for DR on FB axis"""
    if _set_mode("dr", "fb"):
        _set_orientation(math.pi/2,0,0)


def htr():
    """Look for HTR"""
    _set_mode("htr", _builder.previous.variant)


def fr():
    """Look for FR"""
    _set_mode("fr", _builder.previous.variant)


def _set_mode(kind, variant) -> bool:
    step_info = StepInfo(kind, variant)
    if step_info.is_eligible(viz.cube):
        _builder.advance_to(kind, variant)
        while step_info.is_solved(viz.cube) and _builder.previous:
            _builder.advance_to(kind, variant)
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
    print(f"{_builder.build()}")


viz = CubeViz()

def update(builder):
    global _builder
    _builder = builder
    viz.update(builder)

if __name__ == "__main__":
    _builder.listener = update
    threading.Thread(target=lambda: curses.wrapper(read_commands)).start()

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

    viz.run()
