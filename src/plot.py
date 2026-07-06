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
import os

import numpy as np
import plotly.graph_objects as go

from src.utils import compute_midpoints, sat_color

INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input")


def _deg_to_xy(deg: float, r: float = 1.0) -> tuple:
    """Convert orbital degree (0 = top, clockwise) to Cartesian (x, y)."""
    rad = math.radians(deg)
    return r * math.sin(rad), r * math.cos(rad)


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
    interferences = np.array(instance["interferences"]).reshape(num_satellites, num_satellites)
    midpoints = compute_midpoints(boundaries)

    fig = go.Figure()

    # ── Orbit ring ──────────────────────────────────────────────────────────────
    t = np.linspace(0, 360, 361)
    fig.add_trace(go.Scatter(
        x=list(np.sin(np.radians(t))),
        y=list(np.cos(np.radians(t))),
        mode="lines",
        line=dict(color="rgba(160,165,210,0.30)", width=1.5),
        showlegend=False,
        hoverinfo="skip",
    ))

    # ── Degree tick labels ───────────────────────────────────────────────────────
    for deg in range(0, 360, 30):
        xm, ym = _deg_to_xy(deg, r=1.12)
        fig.add_trace(go.Scatter(
            x=[xm], y=[ym],
            mode="text",
            text=[f"{deg}°"],
            textfont=dict(size=9, color="rgba(160,165,210,0.55)"),
            showlegend=False,
            hoverinfo="skip",
        ))

    # ── Interference chords ──────────────────────────────────────────────────────
    max_d = float(interferences.max()) if interferences.max() > 0 else 1.0
    for i in range(num_satellites):
        for j in range(i + 1, num_satellites):
            d = float(interferences[i][j])
            if d < 0.1:
                continue
            opacity = 0.07 + 0.40 * (d / max_d)
            width = 0.6 + 1.8 * (d / max_d)
            xi, yi = _deg_to_xy(midpoints[i])
            xj, yj = _deg_to_xy(midpoints[j])
            fig.add_trace(go.Scatter(
                x=[xi, xj], y=[yi, yj],
                mode="lines",
                line=dict(color=f"rgba(255,195,60,{opacity:.2f})", width=width),
                showlegend=False,
                hoverinfo="text",
                hovertext=f"Interference {i}↔{j}: {d:.3f}",
            ))

    # ── Satellite arcs (allowed ranges) ─────────────────────────────────────────
    r_arc = 1.055
    for i in range(num_satellites):
        span = east[i] - west[i]
        num_pts = max(4, int(span) + 1)
        arc = np.linspace(west[i], east[i], num_pts)
        x_arc = [math.sin(math.radians(d)) * r_arc for d in arc]
        y_arc = [math.cos(math.radians(d)) * r_arc for d in arc]
        fig.add_trace(go.Scatter(
            x=x_arc, y=y_arc,
            mode="lines",
            line=dict(color=sat_color(i), width=10),
            opacity=0.40,
            name=f"Sat {i}  {west[i]:.0f}°–{east[i]:.0f}°",
            showlegend=True,
            hoverinfo="text",
            hovertext=f"Satellite {i}: allowed [{west[i]:.1f}°, {east[i]:.1f}°]",
        ))

    # ── Initial positions (hollow circles) ──────────────────────────────────────
    for i in range(num_satellites):
        xm, ym = _deg_to_xy(midpoints[i], r=r_arc)
        fig.add_trace(go.Scatter(
            x=[xm], y=[ym],
            mode="markers+text",
            marker=dict(
                color=sat_color(i), size=14,
                symbol="circle-open",
                line=dict(width=2.5, color=sat_color(i)),
            ),
            text=[f"  {i}"],
            textposition="middle right",
            textfont=dict(size=11, color=sat_color(i)),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"Satellite {i} initial: {midpoints[i]:.1f}°",
        ))

    # ── Optimized positions (filled circles + arrows) ────────────────────────────
    if positions:
        for i in range(num_satellites):
            xp, yp = _deg_to_xy(positions[i], r=r_arc)
            xm, ym = _deg_to_xy(midpoints[i], r=r_arc)
            if abs(xp - xm) > 0.006 or abs(yp - ym) > 0.006:
                fig.add_annotation(
                    x=xp, y=yp, ax=xm, ay=ym,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=3,
                    arrowwidth=1.8, arrowcolor=sat_color(i), arrowsize=0.9,
                )
            fig.add_trace(go.Scatter(
                x=[xp], y=[yp],
                mode="markers",
                marker=dict(
                    color=sat_color(i), size=17,
                    symbol="circle",
                    line=dict(width=2.5, color="white"),
                ),
                showlegend=False,
                hoverinfo="text",
                hovertext=f"Satellite {i} → {positions[i]:.1f}°",
            ))

    # ── Layout ───────────────────────────────────────────────────────────────────
    fig.update_layout(
        xaxis=dict(visible=False, range=[-1.22, 1.22], constrain="domain"),
        yaxis=dict(visible=False, range=[-1.22, 1.22], scaleanchor="x", scaleratio=1),
        plot_bgcolor="rgba(7,7,22,0.97)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=10),
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.01,
            xanchor="center", x=0.5,
            font=dict(size=9.5, color="rgba(200,205,230,0.85)"),
            bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
        ),
        height=500,
    )
    return fig
