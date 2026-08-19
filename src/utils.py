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

import numpy as np
from demo_configs import INPUT_FILE_PREFIX
from plotly.colors import qualitative

INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input")

_PALETTE = qualitative.Plotly + qualitative.D3 + qualitative.G10


def sat_color(i: int) -> str:
    """Return a color for satellite i, cycling through a predefined palette.
    
    Args:
        i: Satellite index (0-based).
    
    Returns:
        A color string from the palette.
    """
    return _PALETTE[i % len(_PALETTE)]


def load_instances(filename: str) -> list:
    """Load satellite instances from the input directory.

    Args:
        filename: Name of the JSON file containing satellite instances.

    Returns:
        A list of satellite instances loaded from the file.
    """
    path = os.path.join(INPUT_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


def get_instance(num_satellites: int, instance_index: int) -> dict:
    """Load a specific problem instance by satellite count and index.

    Args:
        num_satellites: Number of satellites in the instance.
        instance_index: Index of the instance to load.

    Returns:
        A dictionary representing the satellite instance.
    """
    filename = f"{INPUT_FILE_PREFIX}{num_satellites}.json"
    return load_instances(filename)[instance_index]


def get_interference_matrix(instance: dict) -> np.ndarray:
    """Return an instance's interference values as a square matrix.

    Args:
        instance: Problem instance dict (num_satellites, boundaries, interferences).

    Returns:
        A 2D numpy array of shape (num_satellites, num_satellites) with interference
        values between satellites.
    """
    num_satellites = instance["num_satellites"]
    return np.array(instance["interferences"]).reshape(num_satellites, num_satellites)


def compute_midpoints(boundaries: dict) -> list:
    """Compute the midpoint of each satellite's allowed arc.

    Args:
        boundaries: Dict with keys 'west_boundaries' and 'east_boundaries', each a list of length
            num_satellites with the angular boundaries for each satellite.

    Returns:
        A list of midpoint angles for each satellite.
    """
    east = boundaries["east_boundaries"]
    west = boundaries["west_boundaries"]
    return [(east[j] + west[j]) / 2.0 for j in range(len(east))]


def get_sorted_indices(midpoints: list) -> list:
    """Return satellite indices sorted ascending by midpoint position.

    Args:
        midpoints: List of midpoint angles for each satellite.

    Returns:
        A list of satellite indices sorted by their midpoint angles.
    """
    return [idx for idx, _ in sorted(enumerate(midpoints), key=lambda x: x[1])]
