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

from demo_callbacks import toggle_left_column


@pytest.mark.parametrize(
    "to_collapse_class, class_name_out, aria_expanded_out",
    [
        ("", "collapsed", "false"),
        ("collapsed", "", "true"),
        ("left-column", "left-column collapsed", "false"),
        ("left-column collapsed", "left-column", "true"),
    ],
)
def test_toggle_left_column(to_collapse_class, class_name_out, aria_expanded_out):
    """Test collapsing and expanding UI sections."""

    def run_callback():
        context_value.set(
            AttributeDict(
                **{
                    "triggered_inputs": [
                        {"prop_id": '{"index":0,"type":"collapse-trigger"}.n_clicks'}
                    ]
                }
            )
        )

        return toggle_left_column(1, to_collapse_class)

    ctx = copy_context()

    output = ctx.run(run_callback)
    assert output == (class_name_out, aria_expanded_out)
