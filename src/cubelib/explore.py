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

_mode = ""
_scramble = ""
_running = True
_alg = []
_step_algs = defaultdict(list)


def scramble(str):
    global _scramble
    _scramble = str
    viz.set_cube(str)
    set_mode("")
    viz.set_mode("")


def reset():
    _alg.clear()
    viz.set_cube(_scramble)

def save():
    _step_algs[_mode].append(" ".join(_alg))
    reset()

def list():
    print(f"{_mode.upper()}:")
    for i, alg in enumerate(_step_algs.get(_mode, [])):
        print(f"{i+1}: {alg}")

def append_move(move):
    _alg.append(move)
    viz.set_cube(f"{_scramble} {" ".join(_alg)}")


def eofb():
    set_mode("eofb")


def eorl():
    set_mode("eorl")


def eoud():
    set_mode("eoud")


def set_mode(str):
    global _mode
    _mode = str
    viz.set_mode(_mode)


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
            cmd = input(f"{_mode} - {' '.join(_alg)}> ")
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
