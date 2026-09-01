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

import math

import dash
import numpy as np
import plotly.graph_objects as go
from dash import MATCH, ctx, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from demo_configs import PYOMO_TAB_LABEL, STRIDE_TAB_LABEL
from demo_interface import (
    generate_error_layout,
    generate_instance_stats,
    generate_meter,
    generate_results_layout,
    metric_card,
)
from src.demo_enums import SolverType
from src.plot import create_orbit_figure
from src.utils import get_instance, get_interference_matrix

_SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _format_orderings(n: int) -> str:
    """Format the number of distinct satellite orderings (n!/2) for display.

    The Stride formulation searches over permutations of the satellites, so this
    conveys the combinatorial size of the problem's search space.

    Args:
        n: The number of satellites.

    Returns:
        A string representation of the number of distinct orderings, either in
        full or scientific notation.
    """
    orderings = math.factorial(n) // 2
    if orderings < 1_000_000:
        return f"{orderings:,}"
    exp = len(str(orderings)) - 1
    mantissa = orderings / 10**exp
    return f"{mantissa:.1f} × 10{str(exp).translate(_SUPERSCRIPT)}"


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
def render_input_state(
    num_satellites: str, instance_index: int
) -> tuple[go.Figure, list, bool, bool, str]:
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
    interferences = get_interference_matrix(instance)

    # Count significant interference pairs
    n_pairs = int(np.sum(np.triu(interferences, k=1) > 0.1))
    avg_arc = float(np.mean([east[i] - west[i] for i in range(n)]))
    coverage = avg_arc / 360.0 * 100.0

    fig = create_orbit_figure(instance)

    stats = {
        "Satellites: ": str(n),
        "Possible orderings (n!/2): ": _format_orderings(n),
        "Significant interference pairs: ": str(n_pairs),
        "Avg arc width: ": f"{avg_arc:.1f}° ({coverage:.1f}% of orbit)",
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
    Output("stride-solution", "data", allow_duplicate=True),
    Output("pyomo-solution", "data", allow_duplicate=True),
    [
        Input("run-button", "n_clicks"),
        Input("cancel-button", "n_clicks"),
        State("solver-type-select", "value"),
    ],
    prevent_initial_call=True,
)
def update_tab_loading_state(
    run_click: int, cancel_click: int, solvers: list[str]
) -> tuple[str, bool, bool, str, bool, bool, dict, dict, str, dict, dict]:
    """Updates the tab loading state after the run button
    or cancel button has been clicked.

    Args:
        run_click (int): The number of times the run button has been clicked.
        cancel_click (int): The number of times the cancel button has been clicked.
        solvers (list[str]): The list of selected solvers.

    Returns:
        A tuple containing:

        - str: The label for the Stride tab.
        - bool: True if Stride tab should be disabled, False otherwise.
        - bool: Whether this this a Stride run.
        - str: The label for the Pyomo tab.
        - bool: True if Pyomo tab should be disabled, False otherwise.
        - bool: Whether this is a Pyomo run.
        - dict: Run button style.
        - dict: Cancel button style.
        - str: The value of the tab that should be active.
        - dict: The Stride solution store data.
        - dict: The Pyomo solution store data.
    """

    if ctx.triggered_id == "run-button" and run_click > 0:
        running = ("Loading...", True, True)
        return (
            *(running if f"{SolverType.STRIDE.value}" in solvers else [dash.no_update] * 3),
            *(running if f"{SolverType.PYOMO.value}" in solvers else [dash.no_update] * 3),
            {"display": "none"},
            {},
            "input-tab",
            None,  # clear stale stride solution at run start
            None,  # clear stale pyomo solution at run start
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
            dash.no_update,
            dash.no_update,
        )
    raise PreventUpdate


@dash.callback(
    Output("stride-tab", "disabled", allow_duplicate=True),
    Output("stride-tab", "children", allow_duplicate=True),
    Output("pyomo-tab", "disabled", allow_duplicate=True),
    Output("pyomo-tab", "children", allow_duplicate=True),
    inputs=[
        Input("running-stride", "data"),
        Input("running-pyomo", "data"),
        State("solver-type-select", "value"),
    ],
    prevent_initial_call=True,
)
def enable_tabs_when_done(
    running_stride: bool, running_pyomo: bool, solvers: list[str]
) -> tuple[bool, str, bool, str]:
    """Enable the results tabs only once every selected solver has finished.

    Keeps both tabs in their disabled 'Loading' state until all selected solvers
    have returned, so results appear together when comparing solvers.

    Args:
        running_stride (bool): Whether the Stride solver is running.
        running_pyomo (bool): Whether the Pyomo solver is running.
        solvers (list[str]): The list of selected solvers.

    Returns:
        A tuple containing:

        - bool: Whether the Stride tab should be disabled.
        - str: The label for the Stride tab.
        - bool: Whether the Pyomo tab should be disabled.
        - str: The label for the Pyomo tab.
    """
    if running_stride or running_pyomo:
        raise PreventUpdate

    # Both flags changing in a single update can only come from the cancel handler
    # (solver completions arrive one at a time); a cancelled run has no results to
    # show, so keep the tabs disabled.
    if len(ctx.triggered) > 1:
        raise PreventUpdate

    return (
        False if f"{SolverType.STRIDE.value}" in solvers else dash.no_update,
        STRIDE_TAB_LABEL,
        False if f"{SolverType.PYOMO.value}" in solvers else dash.no_update,
        PYOMO_TAB_LABEL,
    )


@dash.callback(
    Output("run-button", "style", allow_duplicate=True),
    Output("cancel-button", "style", allow_duplicate=True),
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
        A tuple containing:

        - dict: Run button style.
        - dict: Cancel button style.
    """
    if not running_stride and not running_pyomo:
        return {}, {"display": "none"}

    return {"display": "none"}, {}


@dash.callback(
    Output("stride-results", "children", allow_duplicate=True),
    Output("running-stride", "data", allow_duplicate=True),
    Output("stride-solution", "data", allow_duplicate=True),
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
    solvers: list[str],
    time_limit: float,
    num_satellites_val: str,
    instance_index: int,
) -> tuple[list, bool, dict]:
    """Run the Stride solver when the ``Run Optimization`` button is clicked.

    Runs as a background callback: loads the selected problem instance, solves it with the
    Stride hybrid solver (if selected), and returns the results section for the Stride tab.

    Args:
        run_click: The (total) number of times the run button has been clicked.
        solvers: The solvers to use for the optimization run defined by SolverType in demo_enums.py.
        time_limit: The solver time limit.
        num_satellites_val: The number of satellites for the instance.
        instance_index: The index of the specific instance within the file (0-based).

    Returns:
        A tuple containing:

        - list: The results to display in the Stride results tab.
        - bool: Whether this is a Stride run.
        - dict: The Stride solution store data.
    """
    if f"{SolverType.STRIDE.value}" not in solvers:
        return dash.no_update, False, None

    n = int(num_satellites_val)
    instance = get_instance(n, instance_index)

    stride_result: dict = {}

    try:
        from src.stride import solve_instance

        stride_result = solve_instance(instance, time_limit)
    except Exception as exc:
        stride_result = _error_result(exc)

    stride_solution = _solution_store_entry(stride_result)

    return (
        _result_section(instance, stride_result, "D-Wave Stride"),
        False,
        stride_solution,
    )


@dash.callback(
    Output("pyomo-results", "children", allow_duplicate=True),
    Output("running-pyomo", "data", allow_duplicate=True),
    Output("pyomo-solution", "data", allow_duplicate=True),
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
    solvers: list[str],
    time_limit: float,
    num_satellites_val: str,
    instance_index: int,
) -> tuple[list, bool, dict]:
    """Run the Pyomo/Ipopt solver when the ``Run Optimization`` button is clicked.

    Runs as a background callback: loads the selected problem instance, solves it with
    Pyomo and Ipopt (if selected), and returns the results section for the Pyomo tab.

    Args:
        run_click: The (total) number of times the run button has been clicked.
        solvers: The solvers to use for the optimization run defined by SolverType in demo_enums.py.
        time_limit: The solver time limit.
        num_satellites_val: The number of satellites for the instance.
        instance_index: The index of the specific instance within the file (0-based).

    Returns:
        A tuple containing:

        - list: The results to display in the Pyomo results tab.
        - bool: Whether this is a Pyomo run.
        - dict: The Pyomo solution store data.
    """
    if f"{SolverType.PYOMO.value}" not in solvers:
        return dash.no_update, False, None

    n = int(num_satellites_val)
    instance = get_instance(n, instance_index)

    pyomo_result: dict = {}

    try:
        from src.pyomo import solve_instance

        pyomo_result = solve_instance(instance, time_limit)
    except Exception as exc:
        pyomo_result = _error_result(exc)

    pyomo_solution = _solution_store_entry(pyomo_result)

    return (
        _result_section(instance, pyomo_result, "Pyomo / Ipopt"),
        False,
        pyomo_solution,
    )


def _error_result(exc: Exception) -> dict:
    """Build the solver-result dict for a run that raised an exception.

    Args:
        exc: The exception raised while solving.

    Returns:
        A result dict with an 'error' message and empty solution fields.
    """
    return {
        "error": str(exc),
        "objective": None,
        "positions": [],
        "feasible": False,
        "solve_time": 0,
    }


def _solution_store_entry(result: dict) -> dict | None:
    """Build the dcc.Store payload for a solver result (None if unusable).

    Args:
        result: The solver result dict.

    Returns:
        A dict with 'objective' and 'positions' keys, or None if the result is not usable.
    """
    if not result.get("feasible") or result.get("objective") is None or not result.get("positions"):
        return None
    return {"objective": result["objective"], "positions": list(result["positions"])}


def _comparison_card(z: float, other_z: float, other_label: str) -> html.Div:
    """Build a metric card comparing a solver's objective against another.

    Args:
        z: This solver's objective (minimum weighted separation).
        other_z: The other solver's objective.
        other_label: Display name of the other solver.

    Returns:
        A card with the improvement percent when this solver is better, or the shortfall percent
        and a quality bar when worse.
    """
    if z > other_z:
        pct = (z - other_z) / other_z * 100.0
        return metric_card(
            f"Outperforms {other_label}",
            f"{pct:.1f}%",
            class_name="metric-card--better",
        )

    pct = (other_z - z) / other_z * 100.0
    fraction = max(0.0, min(z / other_z, 1.0))

    return metric_card(
        f"Underperforms {other_label} by",
        f"{pct:.1f}%",
        class_name="metric-card--worse",
        additional_html=[generate_meter(fraction)],
    )


@dash.callback(
    Output("stride-results", "children", allow_duplicate=True),
    Output("pyomo-results", "children", allow_duplicate=True),
    inputs=[
        Input("stride-solution", "data"),
        Input("pyomo-solution", "data"),
        State("num-satellites-select", "value"),
        State("instance-index-slider", "value"),
    ],
    prevent_initial_call=True,
)
def update_solution_comparison(
    stride_solution: dict | None,
    pyomo_solution: dict | None,
    num_satellites_val: str,
    instance_index: int,
) -> tuple[list, list]:
    """Fill in the solution-comparison cards once solver results are in.

    Args:
        stride_solution: Stride solution (objective and positions), or None.
        pyomo_solution: Pyomo solution (objective and positions), or None.
        num_satellites_val: The number of satellites for the instance.
        instance_index: The index of the specific instance within the file (0-based).

    Returns:
        A tuple containing:

        - list: The Stride results section with its comparison card.
        - list: The Pyomo results section with its comparison card.
    """
    solutions = {"stride": stride_solution, "pyomo": pyomo_solution}
    available_solutions = {key: solution for key, solution in solutions.items() if solution}
    if not available_solutions:
        raise PreventUpdate

    instance = get_instance(int(num_satellites_val), instance_index)
    labels = {"stride": "Stride", "pyomo": "Pyomo+Ipopt"}

    stride_z = (stride_solution or {}).get("objective")
    pyomo_z = (pyomo_solution or {}).get("objective")
    comparable = stride_z is not None and pyomo_z is not None and stride_z > 0 and pyomo_z > 0
    tied = comparable and math.isclose(stride_z, pyomo_z, rel_tol=1e-6, abs_tol=1e-9)

    outputs = []
    for key in ("stride", "pyomo"):
        solution = solutions[key]
        if not solution:
            outputs.append(dash.no_update)
            continue

        result = {
            "objective": solution["objective"],
            "positions": solution["positions"],
            "feasible": True,
        }
        card = None
        if comparable and not tied:
            other_key = "pyomo" if key == "stride" else "stride"
            card = _comparison_card(
                solutions[key]["objective"],
                solutions[other_key]["objective"],
                labels[other_key],
            )
        outputs.append(_result_section(instance, result, labels[key], comparison_card=card))

    return tuple(outputs)


def _result_section(
    instance: dict,
    result: dict,
    solver_label: str,
    comparison_card: html.Div = None,
) -> list:
    """Build Dash components for a single solver result.

    Args:
        instance: The satellite instance data.
        result: The solver result data.
        solver_label: The label for the solver.
        comparison_card: An optional comparison card to display alongside the results.

    Returns:
        A list of Dash components representing the solver result.
    """
    n = instance["num_satellites"]
    west = instance["boundaries"]["west_boundaries"]
    east = instance["boundaries"]["east_boundaries"]
    positions = result.get("positions") or []

    if result.get("error"):
        return [generate_error_layout(f"{solver_label} error", result["error"])]

    if not positions:
        return [
            generate_error_layout(solver_label, "no feasible solution found within the time limit.")
        ]

    z = result.get("objective") or 0.0

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

    return generate_results_layout(fig, z, table_data, comparison_card)
