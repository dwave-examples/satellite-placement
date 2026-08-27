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
import pytest

from demo_configs import INPUT_FILE_PREFIX, INSTANCE_INDEX, NUM_SATELLITES
from src.utils import (
    _PALETTE,
    INPUT_DIR,
    compute_midpoints,
    get_instance,
    get_interference_matrix,
    get_sorted_indices,
    sat_color,
)


def test_compute_midpoints():
    """Test computing the midpoint of each satellite's allowed arc."""

    boundaries = {"west_boundaries": [0, 100, 30], "east_boundaries": [50, 200, 40]}

    assert compute_midpoints(boundaries) == [25.0, 150.0, 35.0]


def test_get_sorted_indices():
    """Test sorting satellite indices by midpoint position."""

    assert get_sorted_indices([30.0, 10.0, 20.0]) == [1, 2, 0]
    assert get_sorted_indices([5.0, 10.0]) == [0, 1]
    assert get_sorted_indices([]) == []


def test_get_interference_matrix():
    """Test reshaping an instance's interference values into a square matrix."""

    instance = {"num_satellites": 2, "interferences": [[0.0, 0.5], [0.5, 0.0]]}

    output = get_interference_matrix(instance)

    assert output.shape == (2, 2)
    assert output[0][1] == 0.5
    assert np.array_equal(output, output.T)


def test_sat_color():
    """Test the satellite color palette."""

    assert sat_color(0).startswith("#")
    assert sat_color(0) != sat_color(1)
    assert sat_color(0) == sat_color(len(_PALETTE))


def test_get_instance_reads_input_file(monkeypatch, tmp_path):
    """Test loading an instance file from the input directory."""

    instances = [
        {
            "num_satellites": 2,
            "boundaries": {"west_boundaries": [0.0, 90.0], "east_boundaries": [90.0, 180.0]},
            "interferences": [[0.0, 0.5], [0.5, 0.0]],
        }
    ]
    (tmp_path / f"{INPUT_FILE_PREFIX}2.json").write_text(json.dumps(instances))
    monkeypatch.setattr("src.utils.INPUT_DIR", str(tmp_path))

    assert get_instance(2, 0) == instances[0]


@pytest.mark.parametrize("num_satellites", NUM_SATELLITES)
def test_get_instance(num_satellites):
    """Test loading specific problem instances by satellite count and index."""

    for instance_index in (INSTANCE_INDEX["min"], INSTANCE_INDEX["max"]):
        instance = get_instance(num_satellites, instance_index)

        assert instance["num_satellites"] == num_satellites

        west = instance["boundaries"]["west_boundaries"]
        east = instance["boundaries"]["east_boundaries"]
        assert len(west) == num_satellites
        assert len(east) == num_satellites
        assert all(w <= e for w, e in zip(west, east))

        interferences = get_interference_matrix(instance)
        assert interferences.shape == (num_satellites, num_satellites)
        assert np.all(interferences >= 0)
