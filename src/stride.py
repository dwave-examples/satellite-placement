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

import numpy as np
import pandas as pd
import itertools

from dwave.optimization import linprog
from dwave.optimization import Model
from dwave.optimization.mathematical import hstack, concatenate
from dwave.system import LeapHybridNLSampler



def create_model(interferences, boundaries):
    D = interferences

    W = boundaries['west_boundaries']
    E = boundaries['east_boundaries']

    model = Model()

    model.D = D = model.constant(D)
    model.W = W = model.constant(W)
    model.E = E = model.constant(E)

    # todo: check that D/W/E are all the correct size/shape
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

data = []

for num in [5,10,20]:
    file = 'satellite_instances_180_' + str(num) +'.json'
    instances = load_instances(file)
    for i in range(11):
        instance = instances[i]
        num_satellites = instance['num_satellites']
        boundaries = instance['boundaries']
        interferences = np.array(instance['interferences']).reshape(num_satellites, num_satellites)

        midpoints = []
        east = boundaries['east_boundaries']
        west = boundaries['west_boundaries']
        for j in range(num_satellites):
            midpoint = (east[j] + west[j])/2
            midpoints.append(midpoint)

        sorted_indices = [ind for ind, _ in sorted(enumerate(midpoints), key=lambda x: x[1])]

        time_limits = [120]
        for time in time_limits:
            model = create_model(interferences, boundaries)
            model.states.resize(1)
            model.x.set_state(0, sorted_indices)

            solver = LeapHybridNLSampler()
            solver.sample(model, time_limit = time, label = f'sat_{num}_{i}')
            energy = model.objective.state()
            print('energy', energy)
            feas = all(sym.state() for sym in model.iter_constraints())

            data.append({'name': str(num_satellites)+'_'+str(i),
                          'time_limit': time,
                          'energy': energy,
                          'feasibility': feas})
            df = pd.DataFrame(data)
            df.to_csv('nl_leap_satellite_initial-state.csv', index=False)
