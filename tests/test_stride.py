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

import numpy as np

from src.stride import create_model, solve_instance

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
    """Test D-Wave model creation."""

    model = create_model(INTERFERENCES, BOUNDARIES)

    assert model.is_locked()
    assert model.x.size() == NUM_SATELLITES
    assert len(list(model.iter_constraints())) == 1


def test_create_model_lp_state():
    """Test that the model's LP evaluates to a feasible solution for a fixed ordering."""

    model = create_model(INTERFERENCES, BOUNDARIES)
    model.states.resize(1)
    model.x.set_state(0, [0, 1, 2])

    assert all(bool(sym.state()) for sym in model.iter_constraints())

    solution = list(model.solution.state(0))
    thetas, z = solution[:-1], solution[-1]

    assert z > 0
    for k, theta in enumerate(thetas):
        assert BOUNDARIES["west_boundaries"][k] - 1e-6 <= theta
        assert theta <= BOUNDARIES["east_boundaries"][k] + 1e-6


def test_solve_instance(mocker):
    """Test solving an instance, with the hybrid solver mocked out.

    With the solver mocked, the returned state is the LP solution for the
    initial midpoint-sorted ordering, which is evaluated locally.
    """

    mocked_solver = mocker.patch("src.stride.StrideHybridSolver")

    output = solve_instance(INSTANCE, time_limit=5)

    mocked_solver.return_value.sample.assert_called_once()

    assert output["feasible"] is True
    assert output["objective"] > 0
    assert output["solve_time"] >= 0

    west = BOUNDARIES["west_boundaries"]
    east = BOUNDARIES["east_boundaries"]

    assert len(output["positions"]) == NUM_SATELLITES
    for i, position in enumerate(output["positions"]):
        assert west[i] - 1e-6 <= position <= east[i] + 1e-6
