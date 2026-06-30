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

from __future__ import annotations

import numpy as np
import dash
from dash import MATCH, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

from demo_interface import generate_instance_stats, generate_table
from src.demo_enums import SolverType
from src.utils import compute_midpoints, get_instance
from src.plot import create_orbit_figure


@dash.callback(
    Output({"type": "to-collapse-class", "index": MATCH}, "className"),
    Output({"type": "collapse-trigger", "index": MATCH}, "aria-expanded"),
    inputs=[
        Input({"type": "collapse-trigger", "index": MATCH}, "n_clicks"),
        State({"type": "to-collapse-class", "index": MATCH}, "className"),
    ],
    prevent_initial_call=True,
)
def toggle_left_column(collapse_trigger: int, to_collapse_class: str) -> tuple[str, str]:
    """Toggles a 'collapsed' class that hides and shows some aspect of the UI.

    Args:
        collapse_trigger: The (total) number of times a collapse button has been clicked.
        to_collapse_class: Current class name of the thing to collapse, 'collapsed' if not
            visible, empty string if visible.

    Returns:
        A tuple containing:

        - str: The new class name of the thing to collapse.
        - str: The aria-expanded value.
    """

    classes = to_collapse_class.split(" ") if to_collapse_class else []
    if "collapsed" in classes:
        classes.remove("collapsed")
        return " ".join(classes), "true"
    return to_collapse_class + " collapsed" if to_collapse_class else "collapsed", "false"


@dash.callback(
    Output("input-graph", "figure"),
    Output("instance-stats", "children"),
    inputs=[
        Input("num-satellites-select", "value"),
        Input("instance-index-slider", "value"),
    ],
)
def render_input_state(num_satellites: str, instance_index: int) -> tuple[go.Figure, list]:
    """Render the problem-instance orbital diagram on the Input tab.

    Triggered on page load and whenever the instance selection changes.

    Args:
        num_satellites: Number of satellites in the instance.
        instance_index: Index of the specific instance within the file (0-based).

    Returns:
        A tuple containing:

        - go.Figure: The orbital diagram figure.
        - list: The instance statistics.
    """
    n = int(num_satellites)
    instance = get_instance(n, instance_index)
    boundaries = instance["boundaries"]
    west = boundaries["west_boundaries"]
    east = boundaries["east_boundaries"]
    interferences = np.array(instance["interferences"]).reshape(n, n)

    # Count significant interference pairs
    n_pairs = int(np.sum(interferences > 0.1) // 2)
    avg_arc = float(np.mean([east[i] - west[i] for i in range(n)]))
    coverage = avg_arc / 360.0 * 100.0

    fig = create_orbit_figure(
        instance,
        show_interference=True,
    )

    stats = {
        "Satellites: ": str(n),
        "Interference pairs (d > 0.1): ": str(n_pairs),
        "Avg arc width: ": f"{avg_arc:.1f}°",
        "Avg arc coverage: ": f"{coverage:.1f}% of orbit",
    }

    return fig, generate_instance_stats(stats)


@dash.callback(
    Output("stride-results", "children"),
    Output("pyomo-results", "children"),
    inputs=[
        Input("run-button", "n_clicks"),
        State("solver-type-select", "value"),
        State("solver-time-limit", "value"),
        State("num-satellites-select", "value"),
        State("instance-index-slider", "value"),
    ],
    running=[
        (Output("cancel-button", "style"), {}, {"display": "none"}),
        (Output("run-button", "style"), {"display": "none"}, {}),
        (Output("stride-tab", "disabled"), True, False),
        (Output("pyomo-tab", "disabled"), True, False),
        (Output("stride-tab", "children"), "Loading…", "Stride"),
        (Output("pyomo-tab", "children"), "Loading…", "Pyomo"),
        (Output("tabs", "value"), "input-tab", "input-tab"),  # Switch to input tab while running.
    ],
    cancel=[Input("cancel-button", "n_clicks")],
    background=True,
    prevent_initial_call=True,
)
def run_optimization(
    run_click: int,
    solver_type: str,
    time_limit: float,
    num_satellites_val: str,
    instance_index: int,
) -> tuple[str, str]:
    """Runs the optimization and updates UI accordingly.

    This is the main function which is called when the ``Run Optimization`` button is clicked.
    This function takes in all form values and runs the optimization, updates the run/cancel
    buttons, deactivates (and reactivates) the results tab, and updates all relevant HTML
    components.

    Args:
        run_click: The (total) number of times the run button has been clicked.
        solver_type: The solver to use for the optimization run defined by SolverType in demo_enums.py.
        time_limit: The solver time limit.
        num_satellites_val: The number of satellites for the instance.
        instance_index: The index of the specific instance within the file (0-based).

    Returns:
        A tuple containing:

        - str: The results to display in the results tab.
        - str: The comparison results to display in the compare tab.
    """
    run_stride = str(SolverType.STRIDE.value) in (solver_type or [])
    run_pyomo = str(SolverType.PYOMO.value) in (solver_type or [])
    n = int(num_satellites_val)
    instance = get_instance(n, instance_index)

    stride_result: dict = {}
    pyomo_result: dict = {}

    if run_stride:
        try:
            from src.stride import solve_instance as solve_stride
            stride_result = solve_stride(instance, time_limit)
        except Exception as exc:
            stride_result = {"error": str(exc), "objective": None, "positions": [], "feasible": False, "solve_time": 0}

    if run_pyomo:
        try:
            from src.pyomo import solve_instance as solve_pyomo
            pyomo_result = solve_pyomo(instance, time_limit)
        except Exception as exc:
            pyomo_result = {"error": str(exc), "objective": None, "positions": [], "feasible": False, "solve_time": 0}

    if run_stride:
        stride_content = _result_section(instance, stride_result, "D-Wave Stride")
    else:
        stride_content = dash.no_update

    if run_pyomo:
        pyomo_content = _result_section(instance, pyomo_result, "Pyomo / IPOPT")
    else:
        pyomo_content = dash.no_update

    return stride_content, pyomo_content


def _metric_card(label: str, value_str: str, color: str = "inherit") -> html.Div:
    return html.Div(
        className="metric-card",
        children=[
            html.Div(label, className="metric-label"),
            html.Div(value_str, className="metric-value", style={"color": color}),
        ],
    )


def _result_section(instance: dict, result: dict, solver_label: str) -> list:
    """Build Dash components for a single solver result."""
    n = instance["num_satellites"]
    west = instance["boundaries"]["west_boundaries"]
    east = instance["boundaries"]["east_boundaries"]
    midpoints = compute_midpoints(instance["boundaries"])
    positions = result.get("positions") or []

    if result.get("error"):
        return [html.Div(
            className="solver-error",
            children=[html.Strong(f"{solver_label} error: "), html.Span(result["error"])],
        )]

    z = result.get("objective") or 0.0
    feasible = result.get("feasible", False)
    solve_time = result.get("solve_time") or 0.0

    fig = create_orbit_figure(
        instance,
        positions=positions if positions else None,
    )

    # Per-satellite table
    table_data: dict[str, list] = {
        "Satellite": [],
        "Allowed range": [],
        "Initial (midpoint)": [],
        "Optimized position": [],
        "Shift": [],
    }
    for i in range(n):
        pos = positions[i] if positions else midpoints[i]
        table_data["Satellite"].append(i)
        table_data["Allowed range"].append(f"{west[i]:.1f}° – {east[i]:.1f}°")
        table_data["Initial (midpoint)"].append(f"{midpoints[i]:.1f}°")
        table_data["Optimized position"].append(f"{pos:.1f}°")
        table_data["Shift"].append(f"{pos - midpoints[i]:+.1f}°")

    return [
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.Div(
            className="metrics-row",
            children=[
                _metric_card("Objective (z)", f"{z:.3f}°",
                             color="#4ade80" if z > 0 else "#f87171"),
                _metric_card("Feasible", "Yes" if feasible else "No",
                             color="#4ade80" if feasible else "#f87171"),
                _metric_card("Solve time", f"{solve_time:.1f} s"),
            ],
        ),
        html.H4("Per-Satellite Results", className="section-heading"),
        generate_table(table_data),
    ]
