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

import math

import numpy as np
import plotly.graph_objects as go

from src.utils import compute_midpoints, get_interference_matrix, sat_color

# Line color of the hovered-arc overlay while it is empty.
_OVERLAY_IDLE_COLOR = "rgba(0,0,0,0)"

# Distances between points on the figure, in axis units. They approximate marker sizes,
# which are fixed in pixels, at the default plot size.
# Within this distance of a marker's center, a hovered arc point counts as the marker.
_MARKER_HOVER_RADIUS = 0.035
# Markers whose centers are within this distance of each other overlap.
_MARKER_OVERLAP_DISTANCE = 0.07


def _deg_to_xy(deg: float, r: float = 1.0) -> tuple[float, float]:
    """Convert orbital degree (0 = top, clockwise) to Cartesian (x, y).

    Args:
        deg: Orbital degree, in [0, 360].
        r: Optional radius; default is 1.0.

    Returns:
        Tuple of (x, y) coordinates on the circle of radius r.
    """
    rad = math.radians(deg)
    return r * math.sin(rad), r * math.cos(rad)


def _circular_separation(a: float, b: float) -> float:
    """Angular separation between two orbital positions, in [0, 180].

    Args:
        a: First orbital position, in degrees [0, 360].
        b: Second orbital position, in degrees [0, 360].

    Returns:
        Angular separation between a and b, in degrees [0, 180].
    """
    delta = abs(a - b) % 360.0
    return min(delta, 360.0 - delta)


def _restyle_meta(
    role: str, satellites: list[int], base: dict, dim: dict, lit: dict | None = None
) -> dict:
    """Build the trace metadata used to restyle the figure on hover and legend clicks.

    Styles are dicts of trace properties keyed by dotted path (e.g. ``"marker.size"``).

    Args:
        role: What the trace draws: "arc", "marker", "chord", or "overlay". Hovering a
            marker triggers the highlight; arcs are the legend items, so a hidden arc
            marks its satellite as hidden; the overlay redraws the hovered arc on top.
        satellites: Indices of the satellites the trace belongs to.
        base: The trace's style at rest; must match how the trace is created.
        dim: Overrides to ``base`` when the trace is de-emphasized.
        lit: Overrides to ``base`` when the trace is emphasized. Defaults to no change.

    Returns:
        The metadata dict to attach to the trace as ``meta``.
    """
    styles = {"base": base, "dim": {**base, **dim}, "lit": {**base, **(lit or {})}}
    return {"role": role, "satellites": satellites, "styles": styles}


def _marker_restyle_meta(satellite: int, size: float, lit_size: float) -> dict:
    """Build the restyle metadata for a satellite's marker trace.

    Args:
        satellite: Index of the satellite the marker belongs to.
        size: The marker's size at rest; must match how the trace is created.
        lit_size: The marker's size when emphasized.

    Returns:
        The metadata dict to attach to the trace as ``meta``.
    """
    return _restyle_meta(
        "marker",
        [satellite],
        base={
            "opacity": 1.0,
            "marker.size": size,
            "marker.line.width": 2.5,
            "textfont.size": 14,
        },
        dim={"opacity": 0.35},
        lit={"marker.size": lit_size, "marker.line.width": 4, "textfont.size": 18},
    )


def _get_property(trace: dict, path: str):
    """Read a trace property by dotted path, returning None if it is not set.

    Args:
        trace: The trace dict.
        path: Dotted path to the property, e.g. ``"marker.line.width"``.

    Returns:
        The property value, or None.
    """
    value = trace
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _reported_satellite(hover_data: dict | None, traces: list[dict]) -> int | None:
    """Return the satellite whose marker Plotly reports as hovered, or None.

    The arcs run underneath the markers, and with the cursor on a marker Plotly often
    reports an arc point there instead (its own satellite's or an overlapping one). An
    arc point within a marker's footprint is therefore treated as that marker.

    Args:
        hover_data: The graph's ``hoverData``, or None when nothing is hovered.
        traces: The figure's current traces (``figure["data"]``).

    Returns:
        The index of the reported satellite, or None if no marker is hovered.
    """
    points = (hover_data or {}).get("points") or []
    if not points or not 0 <= points[0].get("curveNumber", -1) < len(traces):
        return None

    point = points[0]
    meta = traces[point["curveNumber"]].get("meta") or {}

    if meta.get("role") == "marker":
        return meta["satellites"][0]

    if meta.get("role") == "arc" and "x" in point and "y" in point:
        distance, satellite = min(
            (
                math.hypot(point["x"] - trace["x"][0], point["y"] - trace["y"][0]),
                trace["meta"]["satellites"][0],
            )
            for trace in traces
            if (trace.get("meta") or {}).get("role") == "marker"
        )
        return satellite if distance <= _MARKER_HOVER_RADIUS else None

    return None


def _resolve_hover(
    hover_data: dict | None, traces: list[dict], hover_state: dict | None
) -> dict | None:
    """Decide which satellite the hover highlights.

    Where markers overlap, Plotly's choice of marker under the cursor is not stable: it
    changes as the highlight resizes the markers, which would make the highlight flicker
    between them. Two rules keep it steady:

    - The highlight goes to the topmost marker (the one drawn last) among those
      overlapping the reported one, whichever of them Plotly reports.
    - While Plotly keeps reporting markers that overlap the one that started the current
      highlight, the highlight stays where it is.

    Markers underneath another one therefore cannot be highlighted by hovering.

    Args:
        hover_data: The graph's ``hoverData``, or None when nothing is hovered.
        traces: The figure's current traces (``figure["data"]``).
        hover_state: The state returned for the previous hover event, or None.

    Returns:
        None if no marker is hovered; otherwise a dict with the highlighted satellite
        (``"hovered"``) and the reported satellite that started the highlight (``"anchor"``).
    """
    reported = _reported_satellite(hover_data, traces)
    if reported is None:
        return None

    # Marker centers by satellite; later traces are drawn on top of earlier ones.
    centers = {
        trace["meta"]["satellites"][0]: (i, trace["x"][0], trace["y"][0])
        for i, trace in enumerate(traces)
        if (trace.get("meta") or {}).get("role") == "marker"
    }

    def overlapping(satellite: int) -> list[int]:
        _, x, y = centers[satellite]
        return [
            other
            for other, (_, other_x, other_y) in centers.items()
            if math.hypot(other_x - x, other_y - y) <= _MARKER_OVERLAP_DISTANCE
        ]

    if hover_state and hover_state.get("anchor") in centers:
        if reported in overlapping(hover_state["anchor"]):
            return hover_state

    topmost = max(overlapping(reported), key=lambda satellite: centers[satellite][0])
    return {"hovered": topmost, "anchor": reported}


def orbit_restyle_updates(
    traces: list[dict],
    hover_data: dict | None = None,
    restyle_data: list | None = None,
    hover_state: dict | None = None,
) -> tuple[dict[int, dict], dict | None]:
    """Work out the trace updates that follow a hover or legend click on an orbit figure.

    Hover: while a satellite's marker is hovered, that satellite's arc and marker are
    emphasized, its arc is redrawn above the others, and every other satellite, along
    with the interference chords that do not involve the hovered one, is dimmed.

    Legend: clicking a legend item only hides that satellite's arc, since the arc is the
    legend item; double-clicking hides every other satellite's arc. The markers and chords
    of the hidden satellites are separate traces that stay fully visible, so they are
    dimmed to match. Once more satellites are hidden than shown, the ones still shown are
    the user's selection and are emphasized as well.

    The hover takes precedence while it lasts; the figure then returns to the legend's state.

    Args:
        traces: The figure's current traces (``figure["data"]``).
        hover_data: The graph's ``hoverData``, or None when nothing is hovered.
        restyle_data: The graph's ``restyleData`` if a legend click triggered this update:
            a list of the edited properties and, optionally, the indices of the traces
            they apply to. None otherwise.
        hover_state: The hover state returned by the previous call, or None.

    Returns:
        A tuple containing:

        - dict: Trace index mapped to the properties to change on that trace, keyed by
          dotted path. New ``visible`` values are included because a legend click changes
          them in the browser only, and they must be kept when the figure is redrawn.
        - dict | None: The hover state to pass to the next call.
    """
    visible = {i: trace.get("visible", True) for i, trace in enumerate(traces)}
    edits = restyle_data[0] if restyle_data else {}
    if "visible" in edits:
        values = edits["visible"] if isinstance(edits["visible"], list) else [edits["visible"]]
        indices = restyle_data[1] if len(restyle_data) > 1 else None
        if indices is None:  # no indices means the edit applies to every trace
            indices = range(len(traces))
        for k, trace_index in enumerate(indices):
            visible[trace_index] = values[k % len(values)]

    arcs = {
        trace["meta"]["satellites"][0]: i
        for i, trace in enumerate(traces)
        if (trace.get("meta") or {}).get("role") == "arc"
    }
    hidden = {satellite for satellite, i in arcs.items() if visible[i] is not True}
    emphasize_shown = len(hidden) > len(arcs) - len(hidden)

    hover_state = _resolve_hover(hover_data, traces, hover_state)
    hovered = hover_state["hovered"] if hover_state else None

    updates: dict[int, dict] = {}
    for i, trace in enumerate(traces):
        update = {}
        if visible[i] != trace.get("visible", True):
            update["visible"] = visible[i]

        meta = trace.get("meta")
        if meta and meta["role"] == "overlay":
            # Copy the hovered satellite's arc into the overlay, or empty it.
            if hovered is not None:
                arc = traces[arcs[hovered]]
                overlay = {"x": arc["x"], "y": arc["y"], "line.color": arc["line"]["color"]}
            else:
                overlay = {"x": [None], "y": [None], "line.color": _OVERLAY_IDLE_COLOR}

            for path, value in overlay.items():
                if _get_property(trace, path) != value:
                    update[path] = value
        elif meta:
            if hovered is not None:
                state = "lit" if hovered in meta["satellites"] else "dim"
            elif any(satellite in hidden for satellite in meta["satellites"]):
                state = "dim"
            elif emphasize_shown:
                state = "lit"
            else:
                state = "base"

            for path, value in meta["styles"][state].items():
                if _get_property(trace, path) != value:
                    update[path] = value

        if update:
            updates[i] = update

    return updates, hover_state


def create_orbit_figure(
    instance: dict,
    positions: list = None,
) -> go.Figure:
    """Create an orbital visualization for a satellite placement instance.

    Args:
        instance: Problem instance dict (num_satellites, boundaries, interferences).
        positions: Optional optimized theta values; if None, shows midpoints only.

    Returns:
        A Plotly Figure of the orbital visualization.
    """
    num_satellites = instance["num_satellites"]
    boundaries = instance["boundaries"]
    west = boundaries["west_boundaries"]
    east = boundaries["east_boundaries"]
    interferences = get_interference_matrix(instance)
    midpoints = compute_midpoints(boundaries)

    fig = go.Figure()

    # ── Orbit ring ──────────────────────────────────────────────────────────────
    t = np.linspace(0, 360, 361)
    fig.add_trace(
        go.Scatter(
            x=list(np.sin(np.radians(t))),
            y=list(np.cos(np.radians(t))),
            mode="lines",
            line=dict(color="rgba(160,165,210,0.30)", width=1.5),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # ── Degree tick labels ───────────────────────────────────────────────────────
    for deg in range(0, 360, 30):
        xm, ym = _deg_to_xy(deg, r=1.12)
        fig.add_trace(
            go.Scatter(
                x=[xm],
                y=[ym],
                mode="text",
                text=[f"{deg}°"],
                textfont=dict(size=10.5, color="rgba(160,165,210,0.9)"),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # ── Interference chords ──────────────────────────────────────────────────────
    # Anchor chords to the optimized positions on results plots; fall back to the
    # midpoints for the input/instance view where no solution exists yet.
    chord_pts = positions if positions else midpoints
    max_d = float(interferences.max()) if interferences.max() > 0 else 1.0

    # On solution plots, chord opacity encodes residual interference pressure
    # (weight / achieved separation), normalized against the worst pair of the
    # naive midpoint placement. The reference depends only on the instance, so
    # the Stride and Pyomo plots share one absolute scale: the plot with the
    # more opaque chords is the worse solution.
    ref_pressure = 1.0
    if positions:
        ref_pressure = max(
            (
                float(interferences[i][j])
                / max(_circular_separation(midpoints[i], midpoints[j]), 1e-6)
                for i in range(num_satellites)
                for j in range(i + 1, num_satellites)
                if float(interferences[i][j]) >= 0.1
            ),
            default=1.0,
        )

    for i in range(num_satellites):
        for j in range(i + 1, num_satellites):
            d = float(interferences[i][j])
            if d < 0.1:
                continue
            width = 0.6 + 1.8 * (d / max_d)
            if positions:
                sep = _circular_separation(positions[i], positions[j])
                pressure = d / max(sep, 1e-6)
                opacity = min(0.05 + 0.95 * (pressure / ref_pressure), 1.0)
                color = f"rgba(255,195,60,{opacity:.2f})"
                hovertext = f"Interference {i}↔{j}: weight {d:.3f}, " f"separation {sep:.1f}°"
            else:
                opacity = 0.07 + 0.40 * (d / max_d)
                color = f"rgba(255,195,60,{opacity:.2f})"
                hovertext = f"Interference {i}↔{j}: {d:.3f}"
            xi, yi = _deg_to_xy(chord_pts[i])
            xj, yj = _deg_to_xy(chord_pts[j])
            fig.add_trace(
                go.Scatter(
                    x=[xi, xj],
                    y=[yi, yj],
                    mode="lines",
                    line=dict(color=color, width=width),
                    opacity=1.0,
                    meta=_restyle_meta(
                        "chord", [i, j], base={"opacity": 1.0}, dim={"opacity": 0.35}
                    ),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=hovertext,
                )
            )

    # ── Satellite arcs (allowed ranges) ─────────────────────────────────────────
    r_arc = 1.055
    for i in range(num_satellites):
        span = east[i] - west[i]
        num_pts = max(4, int(span) + 1)
        arc = np.linspace(west[i], east[i], num_pts)
        x_arc = [math.sin(math.radians(d)) * r_arc for d in arc]
        y_arc = [math.cos(math.radians(d)) * r_arc for d in arc]
        fig.add_trace(
            go.Scatter(
                x=x_arc,
                y=y_arc,
                mode="lines",
                line=dict(color=sat_color(i), width=10),
                opacity=0.40,
                meta=_restyle_meta(
                    "arc",
                    [i],
                    base={"opacity": 0.40, "line.width": 10},
                    dim={"opacity": 0.20},
                    lit={"opacity": 1.0, "line.width": 14},
                ),
                name=f"Sat {i}  {west[i]:.0f}°–{east[i]:.0f}°",
                showlegend=True,
                hoverinfo="text",
                hovertext=f"Satellite {i}: allowed [{west[i]:.1f}°, {east[i]:.1f}°]",
            )
        )

    # This trace sits above all the arcs and below the markers; it is empty until
    # a satellite is hovered, when orbit_restyle_updates copies that satellite's arc into it so
    # the hovered satellite's arc is fully visible.
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            line=dict(color=_OVERLAY_IDLE_COLOR, width=14),
            meta=_restyle_meta("overlay", [], base={}, dim={}),
            showlegend=False,
            hoverinfo="skip",  # never the hover target, or it would end the hover it shows
        )
    )

    # ── Initial positions (hollow circles) ──────────────────────────────────────
    if not positions:  # Only shown on the input/instance view.
        for i in range(num_satellites):
            xm, ym = _deg_to_xy(midpoints[i], r=r_arc)
            fig.add_trace(
                go.Scatter(
                    x=[xm],
                    y=[ym],
                    mode="markers+text",
                    marker=dict(
                        color=sat_color(i),
                        size=14,
                        symbol="circle-open",
                        line=dict(width=2.5, color=sat_color(i)),
                    ),
                    text=[f"  {i}"],
                    textposition="middle right",
                    textfont=dict(size=14, color=sat_color(i)),
                    opacity=1.0,
                    meta=_marker_restyle_meta(i, size=14, lit_size=21),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f"Satellite {i} initial: {midpoints[i]:.1f}°",
                )
            )

    # ── Optimized positions (filled circles) ─────────────────────────────────────
    if positions:
        for i in range(num_satellites):
            xp, yp = _deg_to_xy(positions[i], r=r_arc)
            fig.add_trace(
                go.Scatter(
                    x=[xp],
                    y=[yp],
                    mode="markers+text",
                    marker=dict(
                        color=sat_color(i),
                        size=17,
                        symbol="circle",
                        line=dict(width=2.5, color="white"),
                    ),
                    text=[f"  {i}"],
                    textposition="middle right",
                    textfont=dict(size=14, color=sat_color(i)),
                    opacity=1.0,
                    meta=_marker_restyle_meta(i, size=17, lit_size=25),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f"Satellite {i} → {positions[i]:.1f}°",
                )
            )

    # ── Layout ───────────────────────────────────────────────────────────────────
    fig.update_layout(
        xaxis=dict(visible=False, range=[-1.22, 1.22], constrain="domain"),
        yaxis=dict(visible=False, range=[-1.22, 1.22], scaleanchor="x", scaleratio=1),
        plot_bgcolor="rgba(7,7,22,0.97)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=10),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.01,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color="rgb(200,205,230)"),
            bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
        ),
        height=500,
    )
    return fig
