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

import copy
import math

import plotly
import pytest

from src.plot import (
    _MARKER_OVERLAP_DISTANCE,
    _circular_separation,
    _deg_to_xy,
    _get_property,
    create_orbit_figure,
    orbit_restyle_updates,
)
from src.utils import compute_midpoints, get_instance


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (0.0, 0.0, 0.0),
        (0.0, 360.0, 0.0),
        (10.0, 350.0, 20.0),
        (350.0, 10.0, 20.0),
        (90.0, 270.0, 180.0),
        (0.0, 90.0, 90.0),
    ],
)
def test_circular_separation(a, b, expected):
    """Test the angular separation between two orbital positions."""

    assert _circular_separation(a, b) == pytest.approx(expected)


@pytest.mark.parametrize(
    "deg, x, y",
    [
        (0.0, 0.0, 1.0),
        (90.0, 1.0, 0.0),
        (180.0, 0.0, -1.0),
        (270.0, -1.0, 0.0),
    ],
)
def test_deg_to_xy(deg, x, y):
    """Test converting orbital degrees to Cartesian coordinates."""

    output = _deg_to_xy(deg)

    assert output[0] == pytest.approx(x, abs=1e-12)
    assert output[1] == pytest.approx(y, abs=1e-12)

    output = _deg_to_xy(deg, r=2.0)

    assert output[0] == pytest.approx(2 * x, abs=1e-12)
    assert output[1] == pytest.approx(2 * y, abs=1e-12)


def marker_symbols(fig):
    """Return the marker symbols used by the figure's marker traces."""
    return {trace.marker.symbol for trace in fig.data if trace.mode and "markers" in trace.mode}


def test_create_orbit_figure_input_view():
    """Test the orbital diagram for the input view (no solution)."""

    instance = get_instance(5, 0)

    fig = create_orbit_figure(instance)

    assert type(fig) == plotly.graph_objects.Figure
    assert len(fig.data) > 0
    assert marker_symbols(fig) == {"circle-open"}


def test_create_orbit_figure_solution_view():
    """Test the orbital diagram for a solution view (optimized positions)."""

    instance = get_instance(5, 0)
    positions = compute_midpoints(instance["boundaries"])

    fig = create_orbit_figure(instance, positions=positions)

    assert type(fig) == plotly.graph_objects.Figure
    assert marker_symbols(fig) == {"circle"}


def _traces(with_positions=True, num_satellites=5):
    """Return the traces of an orbit figure, as the browser sends them."""
    instance = get_instance(num_satellites, 0)
    positions = compute_midpoints(instance["boundaries"]) if with_positions else None
    return create_orbit_figure(instance, positions=positions).to_plotly_json()["data"]


def _index(traces, role, satellites):
    """Return the index of the trace with the given role and satellites."""
    return next(
        i
        for i, trace in enumerate(traces)
        if trace.get("meta")
        and (trace["meta"]["role"], trace["meta"]["satellites"]) == (role, satellites)
    )


def _hover(traces, trace_index, point=0):
    """Return the hoverData the browser sends when the given trace point is hovered."""
    trace = traces[trace_index]
    return {
        "points": [
            {
                "curveNumber": trace_index,
                "pointNumber": point,
                "x": trace["x"][point],
                "y": trace["y"][point],
            }
        ]
    }


def _hover_marker(traces, satellite):
    """Return the hoverData for hovering the given satellite's marker."""
    return _hover(traces, _index(traces, "marker", [satellite]))


def _arc_point_under_marker(traces, satellite):
    """Return the index of the arc point closest to the satellite's marker."""
    arc = traces[_index(traces, "arc", [satellite])]
    marker = traces[_index(traces, "marker", [satellite])]
    return min(
        range(len(arc["x"])),
        key=lambda k: math.hypot(arc["x"][k] - marker["x"][0], arc["y"][k] - marker["y"][0]),
    )


def _apply(traces, updates):
    """Return the traces with the dotted-path updates applied, as the patched figure holds them."""
    applied = copy.deepcopy(traces)
    for i, properties in updates.items():
        for path, value in properties.items():
            *parents, leaf = path.split(".")
            target = applied[i]
            for key in parents:
                target = target[key]
            target[leaf] = value
    return applied


def _without_default_visible(traces):
    """Drop explicit ``visible: True`` entries, which are equivalent to the key being unset."""
    return [
        {key: value for key, value in trace.items() if (key, value) != ("visible", True)}
        for trace in traces
    ]


def _in_state(trace, state):
    """Return whether every property of the trace matches the given style."""
    return all(
        _get_property(trace, path) == value
        for path, value in trace["meta"]["styles"][state].items()
    )


def _assert_highlighted(traces, satellite):
    """Assert that exactly the given satellite is emphasized and all others are dimmed."""
    for trace in traces:
        if trace.get("meta"):
            assert _in_state(trace, "lit" if satellite in trace["meta"]["satellites"] else "dim")


def _legend_click(traces, visible_by_satellite):
    """Return the restyleData for a legend click that sets the given arcs' visibility."""
    indices = [_index(traces, "arc", [satellite]) for satellite in visible_by_satellite]
    return [{"visible": list(visible_by_satellite.values())}, indices]


@pytest.mark.parametrize("with_positions", [False, True])
def test_create_orbit_figure_restyle_meta(with_positions):
    """Test that satellite and chord traces carry the metadata used to restyle them."""

    traces = _traces(with_positions)

    styled = [trace for trace in traces if trace.get("meta") and trace["meta"]["role"] != "overlay"]
    assert styled

    for trace in styled:
        styles = trace["meta"]["styles"]
        # Traces are created in their resting style, and every style sets the same
        # properties so that moving between styles never leaves one behind.
        assert _in_state(trace, "base")
        assert styles["base"].keys() == styles["dim"].keys() == styles["lit"].keys()
        assert styles["dim"]["opacity"] < styles["base"]["opacity"]

    # Every satellite has an arc and a marker (one satellite each); chords link two.
    roles = [trace["meta"]["role"] for trace in styled]
    assert roles.count("arc") == 5
    assert roles.count("marker") == 5
    assert set(roles) <= {"arc", "marker", "chord"}
    for trace in styled:
        assert len(trace["meta"]["satellites"]) == (2 if trace["meta"]["role"] == "chord" else 1)

    arcs = [trace["meta"]["styles"] for trace in styled if trace["meta"]["role"] == "arc"]
    markers = [trace["meta"]["styles"] for trace in styled if trace["meta"]["role"] == "marker"]

    # Arcs are the legend items, which is what makes a hidden arc a hidden satellite.
    assert all(trace["showlegend"] for trace in styled if trace["meta"]["role"] == "arc")

    for styles in markers:
        assert styles["lit"]["marker.size"] > styles["base"]["marker.size"]
        assert styles["lit"]["marker.line.width"] > styles["base"]["marker.line.width"]

    # Drawing order: the overlay that redraws the hovered arc comes after every arc,
    # which would otherwise tint it, and before every marker.
    overlay = _index(traces, "overlay", [])
    assert (
        max(i for i, t in enumerate(traces) if (t.get("meta") or {}).get("role") == "arc") < overlay
    )
    assert overlay < min(
        i for i, t in enumerate(traces) if (t.get("meta") or {}).get("role") == "marker"
    )
    # It must never be the hover target itself, or it would end the hover it is showing.
    assert traces[overlay]["hoverinfo"] == "skip"


# ── Hover ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("with_positions", [False, True])
def test_orbit_restyle_updates_hover_marker(with_positions):
    """Test that hovering a marker emphasizes its satellite and dims the others."""

    traces = _traces(with_positions)

    updates, state = orbit_restyle_updates(traces, hover_data=_hover_marker(traces, 2))
    hovered = _apply(traces, updates)

    assert state == {"hovered": 2, "anchor": 2}
    _assert_highlighted(hovered, 2)

    # Chords of the hovered satellite keep their resting look; the rest of the figure
    # (orbit ring, degree labels) is never touched.
    assert _index(traces, "chord", [0, 2]) not in updates
    assert all(traces[i].get("meta") for i in updates)

    # The hovered arc is redrawn in the overlay, in its own color, above the other arcs.
    overlay = hovered[_index(hovered, "overlay", [])]
    arc = traces[_index(traces, "arc", [2])]
    assert (overlay["x"], overlay["y"]) == (arc["x"], arc["y"])
    assert overlay["line"]["color"] == arc["line"]["color"]

    # Hovering the same marker again changes nothing, so the figure is not redrawn.
    assert orbit_restyle_updates(
        hovered, hover_data=_hover_marker(traces, 2), hover_state=state
    ) == ({}, state)


def test_orbit_restyle_updates_hover_moves():
    """Test that moving to a marker elsewhere moves the highlight with it."""

    traces = _traces()
    updates, state = orbit_restyle_updates(traces, hover_data=_hover_marker(traces, 2))
    on_two = _apply(traces, updates)

    updates, state = orbit_restyle_updates(
        on_two, hover_data=_hover_marker(traces, 4), hover_state=state
    )

    assert state == {"hovered": 4, "anchor": 4}
    _assert_highlighted(_apply(on_two, updates), 4)


@pytest.mark.parametrize("hover_data", [None, {}, {"points": []}, "arc", "chord"])
def test_orbit_restyle_updates_hover_restore(hover_data):
    """Test that hovering nothing, an arc, or a chord restores the resting styles."""

    traces = _traces()
    updates, state = orbit_restyle_updates(traces, hover_data=_hover_marker(traces, 2))
    highlighted = _apply(traces, updates)

    if hover_data == "arc":
        hover_data = _hover(traces, _index(traces, "arc", [1]))  # the end of the arc
    elif hover_data == "chord":
        hover_data = _hover(traces, _index(traces, "chord", [0, 1]))

    # Only markers trigger the highlight, so at rest these produce no updates at all.
    assert orbit_restyle_updates(traces, hover_data=hover_data) == ({}, None)

    updates, state = orbit_restyle_updates(highlighted, hover_data=hover_data, hover_state=state)
    assert state is None
    assert _apply(highlighted, updates) == traces


@pytest.mark.parametrize("with_positions", [False, True])
@pytest.mark.parametrize("satellite", range(5))
def test_orbit_restyle_updates_hover_arc_under_marker(with_positions, satellite):
    """Test that the arc point underneath a marker counts as hovering that marker.

    Plotly reports either trace there, and can alternate between them as the figure is
    restyled; if they were treated differently the highlight would flicker.
    """

    traces = _traces(with_positions)
    on_arc = _hover(
        traces, _index(traces, "arc", [satellite]), _arc_point_under_marker(traces, satellite)
    )

    updates, state = orbit_restyle_updates(traces, hover_data=_hover_marker(traces, satellite))
    assert updates
    assert orbit_restyle_updates(traces, hover_data=on_arc) == (updates, state)

    # Once highlighted, Plotly switching to the arc point must not change anything.
    assert orbit_restyle_updates(_apply(traces, updates), hover_data=on_arc, hover_state=state) == (
        {},
        state,
    )


def test_orbit_restyle_updates_hover_other_arc_under_marker():
    """Test that another satellite's arc point underneath a marker also counts as the marker.

    Arcs overlap, so with the cursor on a marker Plotly may report a different
    satellite's arc; the highlight should still go to the marker under the cursor.
    """

    traces = _traces()
    marker = traces[_index(traces, "marker", [3])]
    on_other_arc = {
        "points": [
            {"curveNumber": _index(traces, "arc", [2]), "x": marker["x"][0], "y": marker["y"][0]}
        ]
    }

    assert orbit_restyle_updates(traces, hover_data=on_other_arc) == orbit_restyle_updates(
        traces, hover_data=_hover_marker(traces, 3)
    )


def _overlapping(traces, satellite):
    """Return the satellites whose markers overlap the given satellite's marker (itself included)."""
    marker = traces[_index(traces, "marker", [satellite])]
    return [
        trace["meta"]["satellites"][0]
        for trace in traces
        if (trace.get("meta") or {}).get("role") == "marker"
        and math.hypot(trace["x"][0] - marker["x"][0], trace["y"][0] - marker["y"][0])
        <= _MARKER_OVERLAP_DISTANCE
    ]


# In the 30-satellite instance these satellites' markers overlap other markers.
@pytest.mark.parametrize("reported", [1, 4, 5, 12, 28])
def test_orbit_restyle_updates_hover_overlapping_markers(reported):
    """Test that hovering a marker highlights the topmost of the markers overlapping it."""

    traces = _traces(with_positions=False, num_satellites=30)
    overlapping = _overlapping(traces, reported)
    assert len(overlapping) > 1

    updates, state = orbit_restyle_updates(traces, hover_data=_hover_marker(traces, reported))

    # Later satellites are drawn on top of earlier ones.
    assert state == {"hovered": max(overlapping), "anchor": reported}
    _assert_highlighted(_apply(traces, updates), max(overlapping))


def test_orbit_restyle_updates_hover_coincident_markers():
    """Test that two markers in the same place highlight the same satellite, the top one."""

    traces = _traces(with_positions=False, num_satellites=30)

    _, on_lower = orbit_restyle_updates(traces, hover_data=_hover_marker(traces, 4))
    _, on_upper = orbit_restyle_updates(traces, hover_data=_hover_marker(traces, 28))

    assert on_lower["hovered"] == on_upper["hovered"] == 28


def test_orbit_restyle_updates_hover_overlapping_markers_is_steady():
    """Test that the highlight does not move while Plotly alternates between overlapping markers.

    Highlighting resizes the markers, which changes the marker Plotly reports under a
    stationary cursor; following those reports would make the highlight flicker.
    """

    traces = _traces(with_positions=False, num_satellites=30)
    updates, state = orbit_restyle_updates(traces, hover_data=_hover_marker(traces, 5))
    highlighted = _apply(traces, updates)

    for reported in (12, 5, 1, 12, 5):
        assert orbit_restyle_updates(
            highlighted, hover_data=_hover_marker(traces, reported), hover_state=state
        ) == ({}, state)

    # Moving to a marker elsewhere still moves the highlight.
    updates, state = orbit_restyle_updates(
        highlighted, hover_data=_hover_marker(traces, 20), hover_state=state
    )
    assert state["anchor"] == 20
    assert updates


# ── Legend ─────────────────────────────────────────────────────────────────────


def test_orbit_restyle_updates_legend_hide_one():
    """Test that hiding one satellite dims its marker and chords, and only those."""

    traces = _traces()
    arc = _index(traces, "arc", [1])

    updates, state = orbit_restyle_updates(
        traces, restyle_data=_legend_click(traces, {1: "legendonly"})
    )

    assert state is None
    assert updates[arc]["visible"] == "legendonly"

    hidden = _apply(traces, updates)
    for i, trace in enumerate(hidden):
        meta = trace.get("meta")
        if meta and 1 in meta["satellites"]:
            assert _in_state(trace, "dim")
        else:
            # One hidden out of five is not a selection: the rest keep their resting style.
            assert i not in updates

    # Showing it again restores the resting styles.
    updates, _ = orbit_restyle_updates(hidden, restyle_data=_legend_click(traces, {1: True}))
    assert _without_default_visible(_apply(hidden, updates)) == traces


@pytest.mark.parametrize("with_positions", [False, True])
def test_orbit_restyle_updates_legend_isolate(with_positions):
    """Test that isolating one satellite (legend double-click) dims the others and
    emphasizes the one left shown."""

    traces = _traces(with_positions)
    isolate = {satellite: True if satellite == 3 else "legendonly" for satellite in range(5)}

    updates, _ = orbit_restyle_updates(traces, restyle_data=_legend_click(traces, isolate))
    isolated = _apply(traces, updates)

    _assert_highlighted([t for t in isolated if (t.get("meta") or {}).get("role") != "chord"], 3)
    marker = isolated[_index(isolated, "marker", [3])]
    assert marker["marker"]["size"] > traces[_index(traces, "marker", [3])]["marker"]["size"]

    # Double-clicking again shows everything and returns to the resting styles.
    show_all = {satellite: True for satellite in range(5)}
    updates, _ = orbit_restyle_updates(isolated, restyle_data=_legend_click(traces, show_all))
    assert _without_default_visible(_apply(isolated, updates)) == traces


def test_orbit_restyle_updates_legend_emphasis_threshold():
    """Test that shown satellites are emphasized only once more are hidden than shown."""

    traces = _traces()

    def shown_state(num_hidden):
        click = {s: "legendonly" if s < num_hidden else True for s in range(5)}
        updates, _ = orbit_restyle_updates(traces, restyle_data=_legend_click(traces, click))
        marker = _apply(traces, updates)[_index(traces, "marker", [4])]
        return "lit" if _in_state(marker, "lit") else "base"

    assert [shown_state(n) for n in range(5)] == ["base", "base", "base", "lit", "lit"]


def test_orbit_restyle_updates_legend_without_indices():
    """Test that a visibility edit with no trace indices applies to every trace."""

    traces = _traces()
    isolate = {satellite: True if satellite == 3 else "legendonly" for satellite in range(5)}
    updates, _ = orbit_restyle_updates(traces, restyle_data=_legend_click(traces, isolate))
    isolated = _apply(traces, updates)

    for show_all in ([{"visible": True}], [{"visible": [True]}, None]):
        updates, _ = orbit_restyle_updates(isolated, restyle_data=show_all)
        assert _without_default_visible(_apply(isolated, updates)) == traces


@pytest.mark.parametrize("restyle_data", [[{"opacity": [0.5]}, [0]], [{}], [], None])
def test_orbit_restyle_updates_legend_ignores_other_edits(restyle_data):
    """Test that events that do not change visibility produce no updates."""

    assert orbit_restyle_updates(_traces(), restyle_data=restyle_data) == ({}, None)


def test_orbit_restyle_updates_hover_over_legend_selection():
    """Test that a hover takes over from the legend's selection and hands back to it."""

    traces = _traces()
    isolate = {satellite: True if satellite == 3 else "legendonly" for satellite in range(5)}
    updates, _ = orbit_restyle_updates(traces, restyle_data=_legend_click(traces, isolate))
    isolated = _apply(traces, updates)

    # Hovering a dimmed (hidden) satellite's marker highlights it instead.
    updates, state = orbit_restyle_updates(isolated, hover_data=_hover_marker(traces, 0))
    hovered = _apply(isolated, updates)
    _assert_highlighted(hovered, 0)

    # The legend's selection does not use the overlay: the other arcs are hidden, not dimmed.
    assert isolated[_index(isolated, "overlay", [])] == traces[_index(traces, "overlay", [])]

    # Leaving it returns to the legend's selection, with the arcs still hidden.
    updates, state = orbit_restyle_updates(hovered, hover_data=None, hover_state=state)
    assert state is None
    assert _apply(hovered, updates) == isolated
