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

import json
import os

from plotly.colors import qualitative

INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input")

_PALETTE = qualitative.Plotly + qualitative.D3 + qualitative.G10


def sat_color(i: int) -> str:
    return _PALETTE[i % len(_PALETTE)]


def load_instances(filename: str) -> list:
    """Load satellite instances from the input directory."""
    path = os.path.join(INPUT_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


def get_instance(num_satellites: int, instance_index: int) -> dict:
    """Load a specific problem instance by satellite count and index."""
    filename = f"satellite_instances_180_{num_satellites}.json"
    return load_instances(filename)[instance_index]


def compute_midpoints(boundaries: dict) -> list:
    """Compute the midpoint of each satellite's allowed arc."""
    east = boundaries["east_boundaries"]
    west = boundaries["west_boundaries"]
    return [(east[j] + west[j]) / 2.0 for j in range(len(east))]


def get_sorted_indices(midpoints: list) -> list:
    """Return satellite indices sorted ascending by midpoint position."""
    return [idx for idx, _ in sorted(enumerate(midpoints), key=lambda x: x[1])]
