import py_cubelib


class Attempt():
    def __init__(self, scramble: str, solutions: list = None):
        self.scramble = scramble
        self.cube = py_cubelib.Cube(scramble)
        self.solutions = solutions or []

    def find_eos(
            self,
            max_moves: int = 1,
            absolute: bool = True,
            niss: str = "always",
            limit: int = 50
    ) -> "Attempt":
        max, abs_max = (None, max_moves) if absolute else (max_moves, None)
        cfg = py_cubelib.StepConfig(
            kind="eo",
            max=max,
            absolute_max=abs_max,
            step_limit=limit,
            niss=niss
        )
        solutions = py_cubelib.solve_step(self.cube, cfg, self.solutions)
        return Attempt(self.scramble, solutions)

    def add_eo(self, alg: str) -> "Attempt":
        solutions = [py_cubelib.SolutionStep(kind="eo", alg=alg)]
        return Attempt(self.scramble, solutions)

    def find_drs(
            self,
            max_moves: int = 12,
            absolute: bool = True,
            niss: str = "never",
            limit: int = 50,
    ):
        max, abs_max = (None, max_moves) if absolute else (max_moves, None)
        cfg = py_cubelib.StepConfig(
            kind="dr",
            max=max,
            absolute_max=abs_max,
            step_limit=limit,
            niss=niss
        )
        solutions = py_cubelib.solve_step(self.cube, cfg, self.solutions)
        return Attempt(self.scramble, solutions)

    def htr(self, htr: str):
        self.solutions[0].htr = htr
        return self

    def finish(self, finish: str):
        self.solutions[0].finish = finish
        return self

if __name__ == "__main__":
    s = py_cubelib.Solution()
    s.append(py_cubelib.SolutionStep(kind="eo", variant="fB", alg="F", comment=""))
    print(s)
    # attempt = Attempt("R U F")
    # attempt = attempt.find_eos(max_moves=3, absolute=False)
    # print(attempt.solutions[0:10])
    # attempt = attempt.find_drs()
    # print(attempt.solutions[:10])
