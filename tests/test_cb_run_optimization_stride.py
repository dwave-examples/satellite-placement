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

from contextvars import copy_context

import dash
from dash._callback_context import context_value
from dash._utils import AttributeDict

from demo_callbacks import run_optimization_stride
from src.demo_enums import SolverType

STRIDE_VALUE = f"{SolverType.STRIDE.value}"
PYOMO_VALUE = f"{SolverType.PYOMO.value}"

SOLVER_RESULT = {
    "objective": 25.0,
    "positions": [10.0, 150.0, 90.0, 130.0, 40.0],
    "feasible": True,
    "solve_time": 1.5,
}


def run_callback_with(solvers):
    """Run the Stride optimization callback with the given solver selection."""

    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "run-button.n_clicks"}]})
        )

        return run_optimization_stride(1, solvers, 5, "5", 0)

    ctx = copy_context()

    return ctx.run(run_callback)


def test_run_optimization_stride(mocker):
    """Test a successful Stride run."""

    mocker.patch("src.stride.solve_instance", return_value=SOLVER_RESULT)

    results, running, solution = run_callback_with([STRIDE_VALUE, PYOMO_VALUE])

    assert results is not dash.no_update
    assert running is False
    assert solution == {"objective": 25.0, "positions": SOLVER_RESULT["positions"]}


def test_run_optimization_stride_not_selected(mocker):
    """Test that the solver is not run when Stride is not selected."""

    solve = mocker.patch("src.stride.solve_instance", return_value=SOLVER_RESULT)

    results, running, solution = run_callback_with([PYOMO_VALUE])

    assert results is dash.no_update
    assert running is False
    assert solution is None
    solve.assert_not_called()


def test_run_optimization_stride_error(mocker):
    """Test that a solver exception is rendered as an error message."""

    mocker.patch("src.stride.solve_instance", side_effect=RuntimeError("no solver access"))

    results, running, solution = run_callback_with([STRIDE_VALUE])

    assert results[0].className == "solver-error"
    assert "no solver access" in results[0].children[1].children
    assert running is False
    assert solution is None


def test_run_optimization_stride_infeasible(mocker):
    """Test that an infeasible result is rendered as an error message."""

    mocker.patch(
        "src.stride.solve_instance",
        return_value={
            "objective": 0.0,
            "positions": [],
            "feasible": False,
            "solve_time": 0.5,
        },
    )

    results, running, solution = run_callback_with([STRIDE_VALUE])

    assert results[0].className == "solver-error"
    assert running is False
    assert solution is None
