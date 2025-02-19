from fmc_meta import Step

from unittest import TestCase


class TestStep(TestCase):
    def test_move_count(self):
        s = Step(
            name="1",
            moves="U' D F' R' U F2 U2 F2 U B' D2 R U2 R U2 L' D2 R2 B2 L' U2 D2".split(
                " "
            ),
        )
        s2 = Step(
            name="2",
            previous=s,
            moves="R F".split(" "),
            moves_on_inverse="D2".split(" "),
        )
        assert s2.cumulative_move_count == 3
        assert s2.move_count == 3
        s3 = Step(
            name="3",
            previous=s2,
            moves="F2 U2 R".split(" "),
        )
        assert s3.move_count == 2
        assert s3.cumulative_move_count == 5
        s4 = Step(
            name="4",
            previous=s3,
            moves_on_inverse="U F2 U".split(" "),
        )
        assert s4.move_count == 3
        assert s4.cumulative_move_count == 8
        s5 = Step(
            name="5",
            previous=s4,
            moves="R2 F2 L2".split(" "),
        )
        assert s5.move_count == 2
        assert s5.cumulative_move_count == 10
