import os
import subprocess
import sys
import unittest

example_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestSmoke(unittest.TestCase):
    # test that the example runs without failing
    def test_smoke(self):
        file_path = os.path.join(example_dir, 'satellite.py')

        value = subprocess.check_output([sys.executable, file_path])

        for constellation in eval(value):
            self.assertIsInstance(constellation, frozenset)
