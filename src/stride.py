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

from dwave.optimization import linprog
from dwave.optimization import Model
from dwave.optimization.mathematical import hstack, concatenate
from dwave.system import StrideHybridSolver



def create_model(interferences: np.ndarray, boundaries: dict) -> Model:
    """Create a D-Wave mathematical model for the satellite placement problem.
    
    Args:
        interferences: 2D numpy array of shape (num_satellites, num_satellites) with interference
            values between satellites.
        boundaries: Dict with keys 'west_boundaries' and 'east_boundaries', each a list of length
            num_satellites with the angular boundaries for each satellite.

    Returns:
        A D-Wave mathematical Model representing the satellite placement problem.
    """
    D = interferences

    W = boundaries['west_boundaries']
    E = boundaries['east_boundaries']

    model = Model()

    model.D = D = model.constant(D)
    model.W = W = model.constant(W)
    model.E = E = model.constant(E)

    num_satellites = W.size()

    model.x = x = model.list(num_satellites)

    model.d = d = D[x, :][:, x]
    model.w = w = W[x]
    model.e = e = E[x]

    # We want to know the interference for every pair of satellites
    combinations = list(itertools.combinations(range(num_satellites), 2))
    num_rows = len(combinations)

    model.from_ = from_ = model.constant([i for i, j in combinations])
    model.to_ = to_ = model.constant([j for i, j in combinations])

    # We want \forall i < j
    #   d_ij z <= theta_j - theta_i <= 360 - d_ij z
    # Which we can rewrite
    #   theta_i - theta_j + d_ij z <= 0
    #   theta_j - theta_i + d_ij z <= 360
    # So we need theta twice
    theta = np.zeros((num_rows, num_satellites))
    for row, (i, j) in enumerate(combinations):
        theta[row][i] = +1
        theta[row][j] = -1
    model.theta = theta = model.constant(np.vstack((theta, -theta)))

    d_combinations = d[from_, to_]
    model.A = A = hstack((theta, concatenate((d_combinations, d_combinations)).reshape(-1, 1)))
    model.b_ub = b_ub = model.constant([0] * num_rows + [360] * num_rows)

    # We also want \forall i
    #  w_i <= theta_i <= e_i
    # And
    #    0 <= z <= inf
    model.lb = lb = concatenate((w, model.constant([0])))
    model.ub = ub = concatenate((e, model.constant([+1_000])))  # just a large number

    # And finally we want to maximize z
    model.c = c = model.constant([0] * num_satellites + [-1])

    # Ok, we now can put the LP together
    # with unittest.mock.patch("dwave.optimization.mathematical.LinearProgram", SolverSideLP):
    model.lp = lp = linprog(c=c, A_ub=A, b_ub=b_ub, lb=lb, ub=ub)

    # And connect it back to the model
    model.success = model.add_constraint(lp.success)
    model.minimize(lp.fun)

    # This is redundant, but useful for reading the solution
    model.solution = lp.x

    model.lock()
    return model


def solve_instance(instance: dict, time_limit: float) -> dict:
    """Run the D-Wave Stride hybrid solver on a satellite placement instance.

    Args:
        instance: Problem instance dict (num_satellites, boundaries, interferences).
        time_limit: Solver time limit in seconds.

    Returns:
        Dict with keys: objective, positions, feasible, solve_time.
        On error, includes an 'error' key with a message string.
    """
    import time as time_module
    from src.utils import compute_midpoints, get_sorted_indices

    num_satellites = instance["num_satellites"]
    boundaries = instance["boundaries"]
    interferences = np.array(instance["interferences"]).reshape(num_satellites, num_satellites)

    midpoints = compute_midpoints(boundaries)
    sorted_indices = get_sorted_indices(midpoints)

    model = create_model(interferences, boundaries)
    model.states.resize(1)
    model.x.set_state(0, sorted_indices)

    start = time_module.time()
    solver = StrideHybridSolver()
    solver.sample(model, time_limit=int(time_limit), label="Example - Satellite Placement")
    elapsed = time_module.time() - start

    z_value = float(model.objective.state())
    feasible = all(bool(sym.state()) for sym in model.iter_constraints())

    x_perm = list(model.x.state(0))
    sol = list(model.solution.state(0))

    positions = [0.0] * num_satellites
    for k, sat_idx in enumerate(x_perm):
        positions[int(sat_idx)] = float(sol[k])

    # lp.fun = c·x = -z (the model minimizes -z), so negate to get the
    # actual minimum-separation value z that matches the Pyomo objective.
    # sol[-1] is the LP variable for z and is always positive.
    z_value = float(sol[-1])

    return {
        "objective": z_value,
        "positions": positions,
        "feasible": feasible,
        "solve_time": elapsed,
    }
