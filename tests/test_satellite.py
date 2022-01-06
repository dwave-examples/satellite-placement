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
    def test_satellite(self):
        """Verify contents of the output"""

        file_path = os.path.join(example_dir, 'satellite.py')
        data_path = os.path.join(example_dir, 'small.json')
        solver = 'neal'
        viz = False

        output = subprocess.check_output([sys.executable, file_path, data_path, solver])
        output = output.decode('utf-8') # Bytes to str
        output = output.lower()

        if os.getenv('DEBUG_OUTPUT'):
            print("Example output \n" + output)

        with self.subTest(msg="Verify output contains expected keywords \n"):
            self.assertIn("constellation", output)
            self.assertIn("score", output)
        with self.subTest(msg="Verify if error string contains in output \n"):
            self.assertNotIn("error", output)
        with self.subTest(msg="Verify if warning string contains in output \n"):
            self.assertNotIn("warning", output)
