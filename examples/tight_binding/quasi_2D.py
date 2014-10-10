#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@ethz.ch>
# Date:    22.09.2014 14:23:12 CEST
# File:    quasi_2D.py

import sys
sys.path.append("../../src/")
import z2pack.tb as tb

import matplotlib.pyplot as plt

def quasi2D(ax, t1, t2):
    
    H = tb.Hamilton([1, 0, 0], [0, 1, 0], [0, 0, 1])
    
    # create the two atoms
    H.add_atom(([1, 1], 1), [0, 0, 0])
    H.add_atom(([-1, -1], 1), [0.5, 0.5, 0])
    
    # add hopping between different atoms
    H.add_hopping(((0, 0), (1, 1)), tb.vectors.combine([0,-1],[0,-1],0), t1, phase = [1, -1j, 1j, -1])
    H.add_hopping(((0, 1), (1, 0)), tb.vectors.combine([0,-1],[0,-1],0), t1, phase = [1, 1j, -1j, -1])
    
    # add hopping between neighbouring orbitals of the same type
    H.add_hopping((((0, 0), (0, 0)),((0, 1), (0, 1))), tb.vectors.neighbours([0,1]), t2, phase = [1])
    H.add_hopping((((1, 1), (1, 1)),((1, 0), (1, 0))), tb.vectors.neighbours([0,1]), -t2, phase = [1])

    # call to Z2Pack
    tb_system = tb.System(H)
    tb_plane = tb_system.plane(1, 2, 0, pickle_file = './results/quasi_2D.txt')
    tb_plane.wcc_calc(verbose = True, num_strings=20, no_neighbour_check = False, no_iter = False)
    tb_plane.get_res()
    plot = tb_plane.plot(show = False, ax = ax)
    print("t1: {0}, t2: {1}, invariant: {2}".format(t1, t2, tb_plane.invariant()))
    return plot

if __name__ == "__main__":
    fig, axes = plt.subplots(2,2)
    t_values = [[0.2, 0.3], [0.1, 0.4], [-0.2, -0.3], [0.1, 0.2]]
    for i, ax in enumerate(axes.flatten()):
        quasi2D(ax, *t_values[i])
    plt.savefig('quasi2D.pdf', bbox_inches = 'tight')