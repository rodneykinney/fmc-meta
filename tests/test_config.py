from unittest import TestCase
from os import path

from pyhocon import ConfigFactory

from fmc_meta import Meta, main

import fmc_meta.main


class TestConfig(TestCase):
    def test_load_meta(self):
        meta = main.load_meta("near-optimal")
        assert meta is not None
        overrides = {"eo.max_eo_length": "1"}
        meta = main.load_meta("near-optimal", overrides)
        assert meta.eo.max_eo_length == 1
