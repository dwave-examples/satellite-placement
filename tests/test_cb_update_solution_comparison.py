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
import pytest
from dash._callback_context import context_value
from dash._utils import AttributeDict
from dash.exceptions import PreventUpdate

from demo_callbacks import update_solution_comparison

STRIDE_SOLUTION = {"objective": 30.0, "positions": [10.0, 150.0, 90.0, 130.0, 40.0]}
PYOMO_SOLUTION = {"objective": 20.0, "positions": [15.0, 140.0, 95.0, 125.0, 45.0]}


def run_callback_with(stride, pyomo):
    """Run the solution-comparison callback with the given solutions."""

    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "stride-solution.data"}]})
        )

        return update_solution_comparison(stride, pyomo, "5", 0)

    ctx = copy_context()

    return ctx.run(run_callback)


def get_metric_cards(results_layout):
    """Return the metric cards from a solver results layout."""
    return results_layout.children[1].children[0].children


def test_update_solution_comparison():
    """Test that comparison cards are added when both solutions are available."""

    stride_out, pyomo_out = run_callback_with(STRIDE_SOLUTION, PYOMO_SOLUTION)

    stride_cards = get_metric_cards(stride_out)
    pyomo_cards = get_metric_cards(pyomo_out)

    assert len(stride_cards) == 2
    assert "metric-card--better" in stride_cards[1].className
    assert len(pyomo_cards) == 2
    assert "metric-card--worse" in pyomo_cards[1].className


@pytest.mark.parametrize("stride, pyomo", [(STRIDE_SOLUTION, None), (None, PYOMO_SOLUTION)])
def test_update_solution_comparison_one_solution(stride, pyomo):
    """Test that a single available solution is rendered without a comparison card."""

    output = run_callback_with(stride, pyomo)

    for solution, results_layout in zip((stride, pyomo), output):
        if solution is None:
            assert results_layout is dash.no_update
        else:
            assert len(get_metric_cards(results_layout)) == 1


def test_update_solution_comparison_tied():
    """Test that no comparison cards are added when the objectives are tied."""

    tied_pyomo = dict(PYOMO_SOLUTION, objective=STRIDE_SOLUTION["objective"])

    stride_out, pyomo_out = run_callback_with(STRIDE_SOLUTION, tied_pyomo)

    assert len(get_metric_cards(stride_out)) == 1
    assert len(get_metric_cards(pyomo_out)) == 1


def test_update_solution_comparison_no_solutions():
    """Test that the callback is prevented when no solutions are available."""

    with pytest.raises(PreventUpdate):
        run_callback_with(None, None)
