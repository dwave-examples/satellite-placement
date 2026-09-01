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

import plotly
import pytest
from dash._callback_context import context_value
from dash._utils import AttributeDict

from demo_callbacks import render_input_state
from demo_configs import NUM_SATELLITES


@pytest.mark.parametrize("num_satellites", NUM_SATELLITES)
def test_render_input_state(num_satellites):
    """Test rendering the problem-instance orbital diagram on the Input tab."""

    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "num-satellites-select.value"}]})
        )

        return render_input_state(f"{num_satellites}", 0)

    ctx = copy_context()

    fig, stats, stride_disabled, pyomo_disabled, tab = ctx.run(run_callback)

    assert type(fig) == plotly.graph_objects.Figure
    assert len(stats) == 4
    assert stats[0].children[1] == str(num_satellites)
    assert stride_disabled is True
    assert pyomo_disabled is True
    assert tab == "input-tab"
