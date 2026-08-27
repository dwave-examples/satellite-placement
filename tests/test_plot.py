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

import plotly
import pytest

from src.plot import _circular_separation, _deg_to_xy, create_orbit_figure
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
