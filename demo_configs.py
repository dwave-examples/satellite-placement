# Copyright 2026 D-Wave
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

"""This file stores input parameters for the app."""

THUMBNAIL = "static/dwave_logo.svg"

APP_TITLE = "Satellite Placement"
MAIN_HEADER = "Satellite Placement"
DESCRIPTION = """\
Place satellites on a shared orbit so that the minimum angular separation
between every interfering pair is as large as possible, while keeping each
satellite within its allowed arc.
"""

STRIDE_TAB_LABEL = "Stride"
PYOMO_TAB_LABEL = "Pyomo + Ipopt"

#######################################
# Sliders, buttons and option entries #
#######################################

# Number of satellites per instance file
NUM_SATELLITES = [5, 10, 20, 30]

# Index of the specific instance within the file (0-based)
INSTANCE_INDEX = {
    "min": 0,
    "max": 10,
    "step": 1,
    "value": 0,
}

#######################################
# Solver settings                     #
#######################################

# Solver time limit in seconds
SOLVER_TIME = {
    "min": 5,
    "max": 300,
    "step": 5,
    "value": 5,
}
