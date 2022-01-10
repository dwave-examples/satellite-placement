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

.. _link: https://www.dwavesys.com/media/2t2naqik/quantumforsatellitesqubits-4_0.pdf

.. [#btkrd] G. Bass, C. Tomlin, V. Kumar, P. Rihaczek, J. Dulny III.
    Heterogeneous Quantum Computing for Satellite Constellation Optimization:
    Solving the Weighted K-Clique Problem. 2018 Quantum Sci. Technol. 3 024010.
    https://arxiv.org/abs/1709.05381

"""
import argparse
import itertools
import json
import math
import sys

import matplotlib.pyplot as plt
import dimod
import neal
from dwave.system import LeapHybridSampler

def read_in_args():
    """ Read in user specified parameters."""

    parser = argparse.ArgumentParser(description='Satellites example')
    parser.add_argument('file', metavar='file', type=str, help='Input file')
    parser.add_argument('solver', metavar='solver', type=str, help='Solver')
    return parser.parse_args()

# For independent events, Pr(at least one event)=1−Pr(none of the events)
# https://math.stackexchange.com/questions/85849/calculating-the-probability-that-at-least-one-of-a-series-of-events-will-happen
def calculate_score(constellation, data):
    """ Function to calculate constellation score."""

    score = 1
    for v in constellation:
        score *= (1 - data['coverage'][str(v)])
    score = 1 - score
    return score

def build_bqm(data, constellation_size):
    """ Build the bqm for the problem."""

    # don't consider constellations with average score less than score_threshold
    score_threshold = .4

    bqm = dimod.BinaryQuadraticModel.empty(dimod.BINARY)

    # first we want to favor combinations with a high score
    for constellation in itertools.combinations(range(data['num_satellites']), constellation_size):
        # the score is the probability of at least one satellite in the constelation having line of sight over the target at any one time.
        score = calculate_score(constellation, data)

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

    return bqm

def viz(constellations, data):
    """ Visualize the solution"""
    
    angle = 2*math.pi / data["num_satellites"]

    # display scatter plot data
    plt.figure()
    plt.title('Constellations')

    s = 0
    for c in constellations:
        x = []
        y = []
        label = []
        for satellite in c:
            coverage = 1 - data["coverage"][str(satellite)]
            label.append(satellite)
            x.append(coverage*math.cos(s*angle))
            y.append(coverage*math.sin(s*angle))
            s += 1

        x.append(x[0])
        y.append(y[0])
        label.append(label[0])
        plt.plot(x, y, marker = 'o', markersize=1)

    plt.scatter([0], [0], marker = '*', color='#7f7f7f', s=500)
    plt.axis('off')
    
    # save plot
    plt.savefig('constellations.png')

if __name__ == '__main__':

    args = read_in_args()

    with open(args.file, 'r') as fp:
        data = json.load(fp)

    # each of the 12 satellites (labelled 0-11) has a coverage score. This could be
    # calculated as the percentage of time that the Earth region is in range of the
    # satellite

    constellation_size = data['num_satellites'] // data['num_constellations']

    bqm = build_bqm(data, constellation_size)

    if args.solver == 'hss':
        sampleset = LeapHybridSampler().sample(bqm,
                            label='Example - Satellite Placement').aggregate()
    elif args.solver == 'neal':
        sampleset = neal.Neal().sample(bqm, num_reads=100).aggregate()
    else:
        print("satellite.py: Unrecognized solver")
        exit(1)

    constellations = [constellation
                    for constellation, chosen in sampleset.first.sample.items()
                    if chosen]

    tot = 0
    for constellation in constellations:
        score = calculate_score(constellation, data)
        print("Constellation: " + str(constellation) + ", Score: " + str(score))
        tot += score
    print("Total Score: " + str(tot))
    print("Normalized Score (tot / # constellations): " + str((tot / data['num_constellations'])))

    viz(constellations, data)
