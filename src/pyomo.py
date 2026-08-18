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


import itertools

import numpy as np

from pyomo.environ import (
    ConcreteModel, Constraint, Objective, RangeSet, Reals, SolverFactory,
    Var, minimize, value,
)


def create_model(num_satellites: int, boundaries: dict, interferences: np.ndarray) -> ConcreteModel:
    """Create a Pyomo model for the satellite placement problem.

    Args:
        num_satellites: Number of satellites in the instance.
        boundaries: Dict with keys 'west_boundaries' and 'east_boundaries', each a
            list of length num_satellites with the angular boundaries for each satellite.
        interferences: 2D numpy array of shape (num_satellites, num_satellites) with interference
            values between satellites.

    Returns:
        A Pyomo ConcreteModel representing the satellite placement problem.
    """
    west_boundaries = boundaries['west_boundaries']
    east_boundaries = boundaries['east_boundaries']

    combinations = list(itertools.combinations(range(num_satellites), 2))

    model = ConcreteModel()

    model.A = RangeSet(num_satellites)
    model.B = RangeSet(num_satellites)

    model.z = Var(domain = Reals, bounds = (0,1000))

    model.obj = Objective(expr = -model.z, sense = minimize)

    def theta_bounds(model, i):
        return (west_boundaries[i-1], east_boundaries[i-1])

    midpoints = []
    east = boundaries['east_boundaries']
    west = boundaries['west_boundaries']
    for j in range(num_satellites):
        midpoint = (east[j] + west[j])/2
        midpoints.append(midpoint)

    model.thetas = Var(model.A, domain=Reals, bounds=theta_bounds)

    for i in model.A:
        model.thetas[i].value = midpoints[i-1]

    def constraint_rule1(model: ConcreteModel, i: int, j: int):
        """Constraint to ensure that the angular separation between satellites i and j is at least
            the interference value between them, scaled by z.
        """
        if i<j:
            return -interferences[i-1,j-1]*model.z + abs(model.thetas[j] - model.thetas[i]) >= 0
        else:
            return Constraint.Skip

    def constraint_rule2(model: ConcreteModel, i: int, j: int):
        """Constraint to ensure that the angular separation between satellites i and j is at most
            360 degrees minus the interference value between them, scaled by z.
        """
        if i<j:
            return abs(model.thetas[j] - model.thetas[i]) + interferences[i-1,j-1]*model.z <= 360
        else:
            return Constraint.Feasible

    model.constr1 = Constraint(model.A, model.B, rule = constraint_rule1)
    model.constr2 = Constraint(model.A, model.B, rule = constraint_rule2)

    return model


def solve_instance(instance: dict, time_limit: float) -> dict:
    """Run the Pyomo / Ipopt solver on a satellite placement instance.

    Args:
        instance: Problem instance dict (num_satellites, boundaries, interferences).
        time_limit: Solver time limit in seconds.

    Returns:
        Dict with keys: objective, positions, feasible, solve_time.
        On error, includes an 'error' key with a message string.
    """
    import time as time_module

    num_satellites = instance["num_satellites"]
    boundaries = instance["boundaries"]
    interferences = np.array(instance["interferences"]).reshape(num_satellites, num_satellites)

    model = create_model(num_satellites, boundaries, interferences)

    start = time_module.time()
    solver = SolverFactory("ipopt")
    if not solver.available():
        raise RuntimeError(
            "Ipopt solver not found on PATH. "
            "Install it with: brew install ipopt  (macOS) or "
            "apt install coinor-libipopt-dev  (Ubuntu/Debian)."
        )
    solver.options["max_cpu_time"] = time_limit
    solver.solve(model)
    elapsed = time_module.time() - start

    try:
        z_value = float(-value(model.obj))
        positions = [float(value(model.thetas[i])) for i in range(1, num_satellites + 1)]
        feasible = True
    except Exception:
        z_value = 0.0
        positions = []
        feasible = False

    return {
        "objective": z_value,
        "positions": positions,
        "feasible": feasible,
        "solve_time": elapsed,
    }
