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
from dash import Patch
from dash._callback_context import context_value
from dash._utils import AttributeDict
from dash.exceptions import PreventUpdate

from demo_callbacks import highlight_satellites
from src.plot import create_orbit_figure
from src.utils import get_instance

FIGURE = create_orbit_figure(get_instance(5, 0)).to_plotly_json()
HOVER_TRIGGER = [{"prop_id": "input-graph.hoverData"}]
LEGEND_TRIGGER = [{"prop_id": "input-graph.restyleData"}]


def trace_index(role, satellites):
    """Return the index of the figure trace with the given role and satellites."""
    return next(
        i
        for i, trace in enumerate(FIGURE["data"])
        if trace.get("meta")
        and (trace["meta"]["role"], trace["meta"]["satellites"]) == (role, satellites)
    )


def hover(index):
    """Return the hoverData the browser sends when the given trace's first point is hovered."""
    trace = FIGURE["data"][index]
    return {
        "points": [{"curveNumber": index, "pointNumber": 0, "x": trace["x"][0], "y": trace["y"][0]}]
    }


HIDE_SATELLITE_1 = [{"visible": ["legendonly"]}, [trace_index("arc", [1])]]


def run(triggered, hover_data, restyle_data, figure):
    """Run the callback with the given trigger and return its output."""

    def run_callback():
        context_value.set(AttributeDict(**{"triggered_inputs": triggered}))

        return highlight_satellites(hover_data, restyle_data, figure)

    return copy_context().run(run_callback)


def test_highlight_satellites_hover():
    """Test that hovering a marker returns a partial figure update for the satellites."""

    output = run(HOVER_TRIGGER, hover(trace_index("marker", [1])), None, FIGURE)
    assert isinstance(output, Patch)

    operations = output.to_plotly_json()["operations"]
    locations = [op["location"] for op in operations]

    # The hovered marker grows: nested properties are patched by path.
    marker = trace_index("marker", [1])
    assert ["data", marker, "marker", "size"] in locations
    assert ["data", marker, "marker", "line", "width"] in locations
    assert ["data", marker, "textfont", "size"] in locations

    # The hovered arc is copied into the overlay so that it is drawn above the other arcs.
    overlay = trace_index("overlay", [])
    assert ["data", overlay, "x"] in locations
    assert ["data", overlay, "line", "color"] in locations

    # Every other satellite's arc and marker is dimmed.
    dimmed = {loc[1] for loc in locations if loc[0] == "data" and loc[2:] == ["opacity"]}
    for satellite in (0, 2, 3, 4):
        assert trace_index("arc", [satellite]) in dimmed
        assert trace_index("marker", [satellite]) in dimmed

    # The highlighted satellite is recorded on the figure for the next event.
    assert {
        "operation": "Assign",
        "location": ["layout", "meta"],
        "params": {"value": {"hover": {"hovered": 1, "anchor": 1}}},
    } in operations


def test_highlight_satellites_legend():
    """Test that a legend click returns a partial figure update for the hidden satellite."""

    output = run(LEGEND_TRIGGER, None, HIDE_SATELLITE_1, FIGURE)
    assert isinstance(output, Patch)

    operations = output.to_plotly_json()["operations"]
    assert {
        "operation": "Assign",
        "location": ["data", trace_index("arc", [1]), "visible"],
        "params": {"value": "legendonly"},
    } in operations

    # The hidden satellite's arc, marker, and chords are dimmed; nothing else is touched.
    dimmed = {op["location"][1] for op in operations if op["location"][2] == "opacity"}
    assert dimmed == {
        i
        for i, trace in enumerate(FIGURE["data"])
        if trace.get("meta") and 1 in trace["meta"]["satellites"]
    }


@pytest.mark.parametrize(
    "triggered, hover_data, restyle_data, figure",
    [
        (HOVER_TRIGGER, None, None, FIGURE),  # nothing hovered and nothing highlighted
        (HOVER_TRIGGER, hover(trace_index("arc", [1])), None, FIGURE),  # end of an arc
        (HOVER_TRIGGER, hover(trace_index("marker", [1])), None, None),  # no figure yet
        # A legend click left over from a previous figure is not applied on hover.
        (HOVER_TRIGGER, None, HIDE_SATELLITE_1, FIGURE),
        (LEGEND_TRIGGER, None, [{"opacity": [0.5]}, [0]], FIGURE),  # not a visibility change
    ],
)
def test_highlight_satellites_no_update(triggered, hover_data, restyle_data, figure):
    """Test that nothing is updated when the figure already shows the right styles."""

    with pytest.raises(PreventUpdate):
        run(triggered, hover_data, restyle_data, figure)
