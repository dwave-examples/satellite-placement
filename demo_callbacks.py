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

from demo_configs import STRIDE_TAB_LABEL, PYOMO_TAB_LABEL
import numpy as np
import dash
from dash import MATCH, html, ctx
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate



from demo_interface import generate_instance_stats, generate_results_layout
from src.demo_enums import SolverType
from src.utils import get_instance
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
    Output("stride-tab", "disabled"),
    Output("pyomo-tab", "disabled"),
    Output("tabs", "value"),
    inputs=[
        Input("num-satellites-select", "value"),
        Input("instance-index-slider", "value"),
    ],
)
def render_input_state(num_satellites: str, instance_index: int) -> tuple[go.Figure, list, bool, bool, str]:
    """Render the problem-instance orbital diagram on the Input tab.

    Triggered on page load and whenever the instance selection changes.

    Args:
        num_satellites: Number of satellites in the instance.
        instance_index: Index of the specific instance within the file (0-based).

    Returns:
        A tuple containing:

        - go.Figure: The orbital diagram figure.
        - list: The instance statistics.
        - bool: Whether the Stride tab is disabled.
        - bool: Whether the Pyomo tab is disabled.
        - str: The tab to select.
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

    fig = create_orbit_figure(instance)

    stats = {
        "Satellites: ": str(n),
        "Interference pairs (d > 0.1): ": str(n_pairs),
        "Avg arc width: ": f"{avg_arc:.1f}°",
        "Avg arc coverage: ": f"{coverage:.1f}% of orbit",
    }

    return fig, generate_instance_stats(stats), True, True, "input-tab"


@dash.callback(
    Output("stride-tab", "children", allow_duplicate=True),
    Output("stride-tab", "disabled", allow_duplicate=True),
    Output("running-stride", "data", allow_duplicate=True),
    Output("pyomo-tab", "children", allow_duplicate=True),
    Output("pyomo-tab", "disabled", allow_duplicate=True),
    Output("running-pyomo", "data", allow_duplicate=True),
    Output("run-button", "style", allow_duplicate=True),
    Output("cancel-button", "style", allow_duplicate=True),
    Output("tabs", "value", allow_duplicate=True),
    
    [
        Input("run-button", "n_clicks"),
        Input("cancel-button", "n_clicks"),
        State("solver-type-select", "value"),
    ],
    prevent_initial_call=True,
)
def update_tab_loading_state(
    run_click: int, cancel_click: int, solvers: list[str]
) -> tuple[str, bool, bool, str, bool, bool, dict, dict, str]:
    """Updates the tab loading state after the run button
    or cancel button has been clicked.

    Args:
        run_click (int): The number of times the run button has been clicked.
        cancel_click (int): The number of times the cancel button has been clicked.
        solvers (list[str]): The list of selected solvers.

    Returns:
        str: The label for the Stride tab.
        bool: True if Stride tab should be disabled, False otherwise.
        bool: Whether this this a Stride run.
        str: The label for the Pyomo tab.
        bool: True if Pyomo tab should be disabled, False otherwise.
        bool: Whether this is a Pyomo run.
        dict: Run button style.
        dict: Cancel button style.
        str: The value of the tab that should be active.
    """

    if ctx.triggered_id == "run-button" and run_click > 0:
        running = ("Loading...", True, True)
        return (
            *(running if f"{SolverType.STRIDE.value}" in solvers else [dash.no_update] * 3),
            *(running if f"{SolverType.PYOMO.value}" in solvers else [dash.no_update] * 3),
            {"display": "none"},
            {},
            "input-tab",
        )

    if ctx.triggered_id == "cancel-button" and cancel_click > 0:
        return (
            STRIDE_TAB_LABEL,
            dash.no_update,
            False,
            PYOMO_TAB_LABEL,
            dash.no_update,
            False,
            {},
            {"display": "none"},
            dash.no_update,
        )
    raise PreventUpdate


@dash.callback(
    Output("run-button", "style", allow_duplicate=True),
    Output("cancel-button", "style", allow_duplicate=True),
    background=True,
    inputs=[
        Input("running-stride", "data"),
        Input("running-pyomo", "data"),
    ],
    prevent_initial_call=True,
)
def update_button_visibility(running_stride: bool, running_pyomo: bool) -> tuple[dict, dict]:
    """Updates the visibility of the run and cancel buttons.

    Args:
        running_stride (bool): Whether the Stride solver is running.
        running_pyomo (bool): Whether the Pyomo solver is running.

    Returns:
        dict: Run button style.
        dict: Cancel button style.
    """
    if not running_stride and not running_pyomo:
        return {}, {"display": "none"}

    return {"display": "none"}, {}


@dash.callback(
    Output("stride-results", "children", allow_duplicate=True),
    Output("stride-tab", "children", allow_duplicate=True),
    Output("stride-tab", "disabled", allow_duplicate=True),
    Output("running-stride", "data", allow_duplicate=True),
    inputs=[
        Input("run-button", "n_clicks"),
        State("solver-type-select", "value"),
        State("solver-time-limit", "value"),
        State("num-satellites-select", "value"),
        State("instance-index-slider", "value"),
    ],
    cancel=[Input("cancel-button", "n_clicks")],
    background=True,
    prevent_initial_call=True,
)
def run_optimization_stride(
    run_click: int,
    solvers: str,
    time_limit: float,
    num_satellites_val: str,
    instance_index: int,
    ) -> tuple[str, str, bool, bool]:
    """Runs the optimization and updates UI accordingly.

    This is the main function which is called when the ``Run Optimization`` button is clicked.
    This function takes in all form values and runs the optimization, updates the run/cancel
    buttons, deactivates (and reactivates) the results tab, and updates all relevant HTML
    components.

    Args:
        run_click: The (total) number of times the run button has been clicked.
        solvers: The solvers to use for the optimization run defined by SolverType in demo_enums.py.
        time_limit: The solver time limit.
        num_satellites_val: The number of satellites for the instance.
        instance_index: The index of the specific instance within the file (0-based).

    Returns:
        A tuple containing:

        - str: The results to display in the Stride results tab.
        - str: The label for the Stride tab.
        - bool: Whether the Stride tab should be disabled.
        - bool: Whether this is a Stride run.
    """
    if f"{SolverType.STRIDE.value}" not in solvers:
        return dash.no_update, STRIDE_TAB_LABEL, True, False

    n = int(num_satellites_val)
    instance = get_instance(n, instance_index)

    stride_result: dict = {}

    try:
        from src.stride import solve_instance as solve_stride
        stride_result = solve_stride(instance, time_limit)
    except Exception as exc:
        stride_result = {"error": str(exc), "objective": None, "positions": [], "feasible": False, "solve_time": 0}

    return _result_section(instance, stride_result, "D-Wave Stride"), STRIDE_TAB_LABEL, False, False


@dash.callback(
    Output("pyomo-results", "children", allow_duplicate=True),
    Output("pyomo-tab", "children", allow_duplicate=True),
    Output("pyomo-tab", "disabled", allow_duplicate=True),
    Output("running-pyomo", "data", allow_duplicate=True),
    inputs=[
        Input("run-button", "n_clicks"),
        State("solver-type-select", "value"),
        State("solver-time-limit", "value"),
        State("num-satellites-select", "value"),
        State("instance-index-slider", "value"),
    ],
    cancel=[Input("cancel-button", "n_clicks")],
    background=True,
    prevent_initial_call=True,
)
def run_optimization_pyomo(
    run_click: int,
    solvers: str,
    time_limit: float,
    num_satellites_val: str,
    instance_index: int,
) -> tuple[str, str, bool, bool]:
    """Runs the optimization and updates UI accordingly.

    This is the main function which is called when the ``Run Optimization`` button is clicked.
    This function takes in all form values and runs the optimization, updates the run/cancel
    buttons, deactivates (and reactivates) the results tab, and updates all relevant HTML
    components.

    Args:
        run_click: The (total) number of times the run button has been clicked.
        solvers: The solvers to use for the optimization run defined by SolverType in demo_enums.py.
        time_limit: The solver time limit.
        num_satellites_val: The number of satellites for the instance.
        instance_index: The index of the specific instance within the file (0-based).

    Returns:
        A tuple containing:

        - str: The results to display in the Pyomo results tab.
        - str: The label for the Pyomo tab.
        - bool: Whether the Pyomo tab should be disabled.
        - bool: Whether this is a Pyomo run.
    """
    if f"{SolverType.PYOMO.value}" not in solvers:
        return dash.no_update, PYOMO_TAB_LABEL, True, False

    n = int(num_satellites_val)
    instance = get_instance(n, instance_index)

    pyomo_result: dict = {}

    try:
        from src.pyomo import solve_instance as solve_pyomo
        pyomo_result = solve_pyomo(instance, time_limit)
    except Exception as exc:
        pyomo_result = {"error": str(exc), "objective": None, "positions": [], "feasible": False, "solve_time": 0}

    return _result_section(instance, pyomo_result, "Pyomo / IPOPT"), PYOMO_TAB_LABEL, False, False


def _result_section(instance: dict, result: dict, solver_label: str) -> list:
    """Build Dash components for a single solver result."""
    n = instance["num_satellites"]
    west = instance["boundaries"]["west_boundaries"]
    east = instance["boundaries"]["east_boundaries"]
    positions = result.get("positions") or []

    if result.get("error"):
        return [html.Div(
            className="solver-error",
            children=[html.Strong(f"{solver_label} error: "), html.Span(result["error"])],
        )]

    z = result.get("objective") or 0.0
    feasible = result.get("feasible", False)

    fig = create_orbit_figure(
        instance,
        positions=positions if positions else None,
    )

    # Per-satellite table
    table_data: dict[str, list] = {
        "Satellite": [],
        "Allowed range": [],
        "Optimized position": [],
    }
    for i in range(n):
        table_data["Satellite"].append(i)
        table_data["Allowed range"].append(f"{west[i]:.1f}° – {east[i]:.1f}°")
        table_data["Optimized position"].append(f"{positions[i]:.1f}°")

    return generate_results_layout(fig, z, feasible, table_data)
