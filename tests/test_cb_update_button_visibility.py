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

import pytest
from dash._callback_context import context_value
from dash._utils import AttributeDict

from demo_callbacks import update_button_visibility


@pytest.mark.parametrize(
    "running_stride, running_pyomo, run_style, cancel_style, settings_disabled",
    [
        (False, False, {}, {"display": "none"}, False),
        (True, False, {"display": "none"}, {}, True),
        (False, True, {"display": "none"}, {}, True),
        (True, True, {"display": "none"}, {}, True),
    ],
)
def test_update_button_visibility(
    running_stride, running_pyomo, run_style, cancel_style, settings_disabled
):
    """Test the run/cancel button visibility and instance-settings disabling while solvers run."""

    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "running-stride.data"}]})
        )

        return update_button_visibility(running_stride, running_pyomo)

    ctx = copy_context()

    output = ctx.run(run_callback)
    assert output == (run_style, cancel_style, settings_disabled, settings_disabled)
