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

from demo_callbacks import update_tab_loading_state
from demo_configs import PYOMO_TAB_LABEL, STRIDE_TAB_LABEL
from src.demo_enums import SolverType

STRIDE_VALUE = f"{SolverType.STRIDE.value}"
PYOMO_VALUE = f"{SolverType.PYOMO.value}"

LOADING = ("Loading...", True, True)
NO_UPDATE = (dash.no_update,) * 3


@pytest.mark.parametrize(
    "solvers, stride_out, pyomo_out",
    [
        ([STRIDE_VALUE, PYOMO_VALUE], LOADING, LOADING),
        ([STRIDE_VALUE], LOADING, NO_UPDATE),
        ([PYOMO_VALUE], NO_UPDATE, LOADING),
    ],
)
def test_update_tab_loading_state_run(solvers, stride_out, pyomo_out):
    """Test the tab loading state after the run button is clicked."""

    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "run-button.n_clicks"}]})
        )

        return update_tab_loading_state(1, 0, solvers)

    ctx = copy_context()

    output = ctx.run(run_callback)
    assert output == (
        *stride_out,
        *pyomo_out,
        {"display": "none"},
        {},
        "input-tab",
        None,
        None,
    )


def test_update_tab_loading_state_cancel():
    """Test the tab loading state after the cancel button is clicked."""

    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "cancel-button.n_clicks"}]})
        )

        return update_tab_loading_state(1, 1, [STRIDE_VALUE, PYOMO_VALUE])

    ctx = copy_context()

    output = ctx.run(run_callback)
    assert output == (
        STRIDE_TAB_LABEL,
        dash.no_update,
        False,
        PYOMO_TAB_LABEL,
        dash.no_update,
        False,
        {},
        {"display": "none"},
        dash.no_update,
        dash.no_update,
        dash.no_update,
    )


def test_update_tab_loading_state_no_clicks():
    """Test that the callback is prevented when no button has been clicked."""

    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "run-button.n_clicks"}]})
        )

        return update_tab_loading_state(0, 0, [STRIDE_VALUE])

    ctx = copy_context()

    with pytest.raises(PreventUpdate):
        ctx.run(run_callback)
