# Copyright 2020 D-Wave Systems Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
# =============================================================================
"""This example is based on a project by Booz Allen Hamilton researchers
[#btkrd]. See also link_.

The problem is to choose k sub-constellations of m satellites such that the
sum of the average coverage within each constellation is maximized.

There are two versions of the data. The first version runs quickly with
Simulated Annealing. The second version is designed for Hybrid Solver Service.
To run the first one, provide the input file 'small.json' and the solver
name 'neal'. To run the second one, provide the input file 'large.json' and
the solver name 'hss'.

.. _link: https://www.dwavesys.com/sites/default/files/QuantumForSatellitesQubits-4.pdf

.. [#btkrd] G. Bass, C. Tomlin, V. Kumar, P. Rihaczek, J. Dulny III.
    Heterogeneous Quantum Computing for Satellite Constellation Optimization:
    Solving the Weighted K-Clique Problem. 2018 Quantum Sci. Technol. 3 024010.
    https://arxiv.org/abs/1709.05381

"""
import argparse
import dimod
import itertools
import json
import neal
import sys
from dwave.system import LeapHybridSampler

parser = argparse.ArgumentParser(description='Satellites example')
parser.add_argument('file', metavar='file', type=str, help='Input file')
parser.add_argument('solver', metavar='solver', type=str, help='Solver')
args = parser.parse_args()

with open(args.file, 'r') as fp:
    data = json.load(fp)

# each of the 12 satellites (labelled 0-11) has a coverage score. This could be
# calculated as the percentage of time that the Earth region is in range of the
# satellite

constellation_size = data['num_satellites'] // data['num_constellations']

# don't consider constellations with average score less than score_threshold
score_threshold = .4

bqm = dimod.AdjVectorBQM.empty(dimod.BINARY)

# first we want to favor combinations with a high score
for constellation in itertools.combinations(range(data['num_satellites']), constellation_size):
    # the score is the average coverage for a constellation
    score = sum(data['coverage'][str(v)] for v in constellation) / constellation_size

    # to make it smaller, throw out the combinations with a score below
    # a set threshold
    if score < score_threshold:
        continue

    # we subtract the score because we want to minimize the energy
    bqm.add_variable(frozenset(constellation), -score)

# next we want to penalize pairs that share a satellite. We choose 2 because
# because we don't want it to be advantageous to pick both in the case that
# they both have 100% coverage
for c0, c1 in itertools.combinations(bqm.variables, 2):
    if c0.isdisjoint(c1):
        continue
    bqm.add_interaction(c0, c1, 2)

# finally we wish to choose num_constellations variables. We pick strength of 1
# because we don't want it to be advantageous to violate the constraint by
# picking more variables
bqm.update(dimod.generators.combinations(bqm.variables, data['num_constellations'], strength=1))

if args.solver == 'hss':
    sampleset = LeapHybridSampler().sample(bqm).aggregate()
elif args.solver == 'neal':
    sampleset = neal.Neal().sample(bqm, num_reads=100).aggregate()
else:
    print("satellite.py: Unrecognized solver")
    exit(1)

constellations = [constellation
                  for constellation, chosen in sampleset.first.sample.items()
                  if chosen]

print(constellations)
