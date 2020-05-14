# Copyright 2019 D-Wave Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

    def test_satellite(self):
        """Verify contents of the output"""

        file_path = os.path.join(example_dir, 'satellite.py')
        output = subprocess.check_output([sys.executable, file_path])
        output = str(output).upper()
        if os.getenv('DEBUG_OUTPUT'):
            print("Example output \n"+ output)

        with self.subTest(msg="Verify if output contains '[frozenset({' \n"):
            self.assertIn("[frozenset({".upper(), output)
        with self.subTest(msg="Verify if error string contains in output \n"):
            self.assertNotIn("ERROR", output)
        with self.subTest(msg="Verify if warning string contains in output \n"):
            self.assertNotIn("WARNING", output)
