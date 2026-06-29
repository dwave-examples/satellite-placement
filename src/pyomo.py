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

from pyomo.environ import ConcreteModel, RangeSet, Var, Objective, Constraint, Reals, minimize, SolverFactory
import itertools


def create_model(num_satellites, boundaries, interferences):
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

    def constraint_rule1(model, i, j):
        if i<j:
            return -interferences[i-1,j-1]*model.z + abs(model.thetas[j] - model.thetas[i]) >= 0
        else:
            return Constraint.Skip

    def constraint_rule2(model, i,j):
        if i<j:
            return abs(model.thetas[j] - model.thetas[i]) + interferences[i-1,j-1]*model.z <= 360
        else: return Constraint.Feasible

    model.constr1 = Constraint(model.A, model.B, rule = constraint_rule1)
    model.constr2 = Constraint(model.A, model.B, rule = constraint_rule2)

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
        model = create_model(num_satellites, boundaries, interferences)
        print(f'model {i} created')
        # model.pprint()

        time_limits = [30, 60]
        for time in time_limits:
            print('running with ', time, ' seconds')
            solver = SolverFactory('ipopt')
            solver.options['max_cpu_time'] = time
            solver.solve(model)

            energy = model.obj()
            print("Objective value:", energy)

            data.append({'name': str(num_satellites)+'_'+str(i),
                'time_limit': time,
                'energy': energy})
            df = pd.DataFrame(data)
            df.to_csv('pyomo_ipopt_satellite_initial.csv', index=False)
