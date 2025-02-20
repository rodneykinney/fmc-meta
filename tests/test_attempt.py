from unittest import TestCase
import multiprocessing

import fmc_meta
from fmc_meta import Meta

from fmc_meta.strategies import GeneralEO, OptimalDR, OptimalFinish
from fmc_meta.main import attempt


class TestStep(TestCase):
    def test_attempt(self):
        meta = Meta(
            eo_strategy=GeneralEO(
                max_eo_length=1, check_inverse=True, max_niss_split=0, retain=4
            ),
            dr_strategy=OptimalDR(max_dr_length=2, retain=4),
            finish_strategy=OptimalFinish(),
        )
        solutions = attempt(meta, "R U F".split(" "))
        assert len(solutions.eos) == 2
        assert len(solutions.drs) == 4
        for f in solutions.finishes:
            assert f.cumulative_move_count == 3
