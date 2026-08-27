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

from itertools import combinations

import numpy as np
import pytest

from pyomo.environ import SolverFactory
from src.pyomo import create_model, solve_instance

NUM_SATELLITES = 3
BOUNDARIES = {
    "west_boundaries": [0.0, 60.0, 120.0],
    "east_boundaries": [90.0, 180.0, 240.0],
}
INTERFERENCES = np.array(
    [
        [0.0, 0.5, 0.2],
        [0.5, 0.0, 0.8],
        [0.2, 0.8, 0.0],
    ]
)
INSTANCE = {
    "num_satellites": NUM_SATELLITES,
    "boundaries": BOUNDARIES,
    "interferences": INTERFERENCES.tolist(),
}


def test_create_model():
    """Test Pyomo model creation."""

    model = create_model(NUM_SATELLITES, BOUNDARIES, INTERFERENCES)

    assert len(model.A) == NUM_SATELLITES
    assert len(model.B) == NUM_SATELLITES
    assert model.z.bounds == (0, 1000)

    west = BOUNDARIES["west_boundaries"]
    east = BOUNDARIES["east_boundaries"]
    for i in model.A:
        assert model.thetas[i].bounds == (west[i - 1], east[i - 1])
        assert model.thetas[i].value == pytest.approx((west[i - 1] + east[i - 1]) / 2)

    # The separation constraints should cover exactly the i < j satellite pairs; a
    # wrong-sized index set would silently drop pairs rather than error. Constraint.Skip
    # omits the i >= j entries from constr1, while Constraint.Feasible keeps trivial
    # placeholders in constr2, so constr1 is checked exactly and constr2 for membership.
    pairs = list(combinations(range(1, NUM_SATELLITES + 1), 2))
    assert sorted(model.constr1.keys()) == pairs
    assert all(pair in model.constr2 for pair in pairs)


def test_solve_instance_no_ipopt(mocker):
    """Test that a missing Ipopt install raises a RuntimeError."""

    factory = mocker.patch("src.pyomo.SolverFactory")
    factory.return_value.available.return_value = False

    with pytest.raises(RuntimeError):
        solve_instance(INSTANCE, time_limit=5)


@pytest.mark.skipif(
    not SolverFactory("ipopt").available(exception_flag=False),
    reason="Ipopt is not installed",
)
def test_solve_instance():
    """Test solving an instance with Ipopt."""

    output = solve_instance(INSTANCE, time_limit=10)

    assert output["feasible"] is True
    assert output["objective"] > 0
    assert output["solve_time"] >= 0

    west = BOUNDARIES["west_boundaries"]
    east = BOUNDARIES["east_boundaries"]

    assert len(output["positions"]) == NUM_SATELLITES
    for i, position in enumerate(output["positions"]):
        # Ipopt's interior-point method can overshoot bounds by ~1e-6
        assert west[i] - 1e-4 <= position <= east[i] + 1e-4
