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

from demo_callbacks import enable_tabs_when_done
from demo_configs import PYOMO_TAB_LABEL, STRIDE_TAB_LABEL
from src.demo_enums import SolverType

STRIDE = f"{SolverType.STRIDE.value}"
PYOMO = f"{SolverType.PYOMO.value}"

LOADING = "Loading..."
ONE_TRIGGER = [{"prop_id": "running-stride.data"}]
BOTH_TRIGGERS = [{"prop_id": "running-stride.data"}, {"prop_id": "running-pyomo.data"}]


@pytest.mark.parametrize("triggered", [ONE_TRIGGER, BOTH_TRIGGERS])
@pytest.mark.parametrize(
    "solvers, stride_label, pyomo_label, stride_disabled_out, pyomo_disabled_out",
    [
        ([STRIDE, PYOMO], LOADING, LOADING, False, False),
        ([STRIDE], LOADING, PYOMO_TAB_LABEL, False, dash.no_update),
        ([PYOMO], STRIDE_TAB_LABEL, LOADING, dash.no_update, False),
    ],
)
def test_enable_tabs_when_done(
    triggered, solvers, stride_label, pyomo_label, stride_disabled_out, pyomo_disabled_out
):
    """Test that the results tabs are enabled once all selected solvers finish."""

    def run_callback():
        context_value.set(AttributeDict(**{"triggered_inputs": triggered}))

        return enable_tabs_when_done(False, False, solvers, stride_label, pyomo_label)

    ctx = copy_context()

    output = ctx.run(run_callback)
    assert output == (
        stride_disabled_out,
        STRIDE_TAB_LABEL,
        pyomo_disabled_out,
        PYOMO_TAB_LABEL,
    )


@pytest.mark.parametrize(
    "running_stride, running_pyomo",
    [(True, False), (False, True), (True, True)],
)
def test_enable_tabs_when_still_running(running_stride, running_pyomo):
    """Test that the tabs stay disabled while any solver is still running."""

    def run_callback():
        context_value.set(AttributeDict(**{"triggered_inputs": ONE_TRIGGER}))

        return enable_tabs_when_done(
            running_stride, running_pyomo, [STRIDE, PYOMO], LOADING, LOADING
        )

    ctx = copy_context()

    with pytest.raises(PreventUpdate):
        ctx.run(run_callback)


@pytest.mark.parametrize("triggered", [ONE_TRIGGER, BOTH_TRIGGERS])
@pytest.mark.parametrize("solvers", [[STRIDE, PYOMO], [STRIDE], [PYOMO]])
def test_enable_tabs_when_cancelled(triggered, solvers):
    """Test that the tabs stay disabled after a cancel, which resets the tab labels."""

    def run_callback():
        context_value.set(AttributeDict(**{"triggered_inputs": triggered}))

        return enable_tabs_when_done(False, False, solvers, STRIDE_TAB_LABEL, PYOMO_TAB_LABEL)

    ctx = copy_context()

    with pytest.raises(PreventUpdate):
        ctx.run(run_callback)
