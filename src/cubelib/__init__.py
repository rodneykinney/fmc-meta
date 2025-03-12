
from py_cubelib import (Solution as RSolution, Cube as RCube,)

class Attempt():
    def __init__(self, cube: RCube):
        self.cube = cube
        self.solutions = [RSolution()]

    def eo(self, max_moves: int = 1, check_inverse: bool = True, max_niss_split: int = 0, retain: int = 50):
        self.solutions[0].eo = eo
        return self

    def dr(self, dr: str):
        self.solutions[0].dr = dr
        return self

    def htr(self, htr: str):
        self.solutions[0].htr = htr
        return self

    def finish(self, finish: str):
        self.solutions[0].finish = finish
        return self

def hello():
    print("Hello from py_cubelib!")