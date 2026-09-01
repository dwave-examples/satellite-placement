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

import pytest
from dash import html

from demo_callbacks import (
    _comparison_card,
    _error_result,
    _format_orderings,
    _result_section,
    _solution_store_entry,
)

ERROR_RESULT = {
    "error": "boom",
    "objective": None,
    "positions": [],
    "feasible": False,
    "solve_time": 0,
}

INSTANCE = {
    "num_satellites": 3,
    "boundaries": {
        "west_boundaries": [0.0, 60.0, 120.0],
        "east_boundaries": [90.0, 180.0, 240.0],
    },
    "interferences": [
        [0.0, 0.5, 0.2],
        [0.5, 0.0, 0.8],
        [0.2, 0.8, 0.0],
    ],
}


@pytest.mark.parametrize(
    "n, expected",
    [
        (3, "3"),
        (5, "60"),
        (9, "181,440"),
        (10, "1.8 × 10⁶"),
        (20, "1.2 × 10¹⁸"),
    ],
)
def test_format_orderings(n, expected):
    """Test formatting of the number of distinct satellite orderings."""

    assert _format_orderings(n) == expected


def test_error_result():
    """Test the solver-result dict built from an exception."""

    output = _error_result(ValueError("boom"))

    assert output == ERROR_RESULT


@pytest.mark.parametrize(
    "result, expected",
    [
        (
            {"objective": 25.0, "positions": [1.0, 2.0], "feasible": True},
            {"objective": 25.0, "positions": [1.0, 2.0]},
        ),
        (
            {"objective": 0.0, "positions": [1.0, 2.0], "feasible": True},
            {"objective": 0.0, "positions": [1.0, 2.0]}
        ),
        ({"objective": 25.0, "positions": [1.0, 2.0], "feasible": False}, None),
        ({"objective": None, "positions": [1.0, 2.0], "feasible": True}, None),
        ({"objective": 25.0, "positions": [], "feasible": True}, None),
    ],
)
def test_solution_store_entry(result, expected):
    """Test building the dcc.Store payload from a solver result."""

    assert _solution_store_entry(result) == expected


def test_comparison_card_better():
    """Test the comparison card when this solver outperforms the other."""

    card = _comparison_card(30.0, 20.0, "Pyomo+Ipopt")

    assert "metric-card--better" in card.className
    assert card.children[0].children == "Outperforms Pyomo+Ipopt"
    assert card.children[1].children == "50.0%"
    assert len(card.children) == 2


def test_comparison_card_worse():
    """Test the comparison card when this solver underperforms the other."""

    card = _comparison_card(20.0, 30.0, "Stride")

    assert "metric-card--worse" in card.className
    assert card.children[0].children == "Underperforms Stride by"
    assert card.children[1].children == "33.3%"
    assert card.children[2].children.style["width"] == "66.7%"


def test_result_section():
    """Test the results section for a feasible solver result."""

    result = {
        "objective": 25.0,
        "positions": [45.0, 120.0, 200.0],
        "feasible": True,
    }

    output = _result_section(INSTANCE, result, "Stride Hybrid Solver")

    assert isinstance(output, html.Div)
    assert output.className == "graph-layout"


def test_result_section_error():
    """Test the results section for a solver run that raised an error."""

    output = _result_section(INSTANCE, ERROR_RESULT, "Stride Hybrid Solver")

    assert output[0].className == "solver-error"
    assert output[0].children[0].children == "Stride Hybrid Solver error: "
    assert output[0].children[1].children == "boom"


def test_result_section_no_positions():
    """Test the results section when no feasible solution was found."""

    result = {"objective": None, "positions": [], "feasible": False}

    output = _result_section(INSTANCE, result, "Pyomo / Ipopt")

    assert output[0].className == "solver-error"
    assert "no feasible solution" in output[0].children[1].children
