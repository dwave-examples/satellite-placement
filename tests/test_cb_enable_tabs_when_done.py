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


@pytest.mark.parametrize(
    "solvers, stride_disabled_out, pyomo_disabled_out",
    [
        ([STRIDE, PYOMO], False, False),
        ([STRIDE], False, dash.no_update),
        ([PYOMO], dash.no_update, False),
    ],
)
def test_enable_tabs_when_done(solvers, stride_disabled_out, pyomo_disabled_out):
    """Test that the results tabs are enabled once all selected solvers finish."""

    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "running-stride.data"}]})
        )

        return enable_tabs_when_done(False, False, solvers)

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
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "running-stride.data"}]})
        )

        return enable_tabs_when_done(running_stride, running_pyomo, [STRIDE, PYOMO])

    ctx = copy_context()

    with pytest.raises(PreventUpdate):
        ctx.run(run_callback)


def test_enable_tabs_when_cancelled():
    """Test that the tabs stay disabled when both running flags change at once (cancel)."""

    def run_callback():
        context_value.set(
            AttributeDict(
                **{
                    "triggered_inputs": [
                        {"prop_id": "running-stride.data"},
                        {"prop_id": "running-pyomo.data"},
                    ]
                }
            )
        )

        return enable_tabs_when_done(False, False, [STRIDE, PYOMO])

    ctx = copy_context()

    with pytest.raises(PreventUpdate):
        ctx.run(run_callback)
