#!/usr/bin/python3.3
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@ethz.ch>
# Date:    21.03.2014 11:46:38 CET
# File:    z2pack.py

from __future__ import print_function

import python_tools.string_tools as string_tools

import sys
import time
import copy
import pickle
import numpy as np
import scipy.linalg as la
import matplotlib.pyplot as plt

#-----------------------------------------------------------------------#
#-----------------------------------------------------------------------#
#                           LIBRARY CORE                                #
#-----------------------------------------------------------------------#
#-----------------------------------------------------------------------#
class Z2PackSystem:
    """
    abstract Base Class for Z2Pack systems (Interface definition)
    
    :param M_handle_creator: takes (string_dir, plane_pos_dir, plane_pos) and creates an M_handle --> M_handle(kx, N): creates M-matrices
    
    :param kwargs: passed to Z2PackPlane constructor unless overwritten by plane() kwargs
    """
    
    def __init__(self, M_handle_creator, **kwargs):
        self._defaults = kwargs
        self._M_handle_creator = M_handle_creator
    

    def plane(self, string_dir, plane_pos_dir, plane_pos, **kwargs):
        """
        :param string_dir: direction of the string of k-points
        :type string_dir: int
        :param plane_pos_dir: index of the reciprocal lattice vector not in the plane
        :type plane_pos_dir: int
        :param plane_pos: position of the plane along ``plane_pos_dir``
        :type plane_pos: float
        :param kwargs: passed to Z2PackPlane constructor. Take precedence over kwargs from Z2PackSystem constructor.
        """
        # updating keyword arguments
        kw_arguments = copy.copy(self._defaults)
        kw_arguments.update(kwargs)
        
        # creating M_handle
        if(string_dir == plane_pos_dir):
            raise ValueError('strings cannot be perpendicular to the plane')
        
        return Z2PackPlane(   
                                    self._M_handle_creator(string_dir, plane_pos_dir, plane_pos),
                                    **kw_arguments
                                )

class Z2PackPlane:
    """
    Specifies a plane in the 3D system, on which to calculate the topological invariant. This is achieved via the M_handle input variable. The M_handle is created by Z2PackSystem.plane(), and as such is specific to the type of Z2Pack calculation (Fp, Tb, ...)

    :param M_handle:        should create a list of MMN given (k, N)
    :type M_handle:         function
    
    :param pickle_file:     path to file for saving using pickle
    :type pickle_file:      str
        
    :param kwargs: Are passed to ``wcc_calc``. Kwargs specified in ``wcc_calc`` take precedence
    """
    
    def __init__(   self, 
                    M_handle, 
                    pickle_file = "res_pickle.txt", 
                    **kwargs):
        self._M_handle = M_handle
        self._pickle_file = pickle_file
        self._defaults = {  
                            'no_iter': False,
                            'no_neighbour_check': False,
                            'wcc_tol': 1e-2,
                            'gap_tol': 2e-2,
                            'max_iter': 10,
                            'min_neighbour_dist': 0.01,
                            'use_pickle': True,
                            'num_strings': 11,
                            'verbose': True
                            }
        self._defaults.update(kwargs)
        
    def wcc_calc(self, **kwargs):
        """
        calculating the wcc of the system
        - automated convergence in string direction
        - automated check for distance between gap and wcc -> add string
        
        kwargs:
        ~~~~~~
        no_iter:            turns iterations off
        no_neighbour_check: turns neighbour checks off
        wcc_tol:            maximum movement of wcc between two steps 
                            for convergence
        gap_tol:            minimum size of gap between the largest gap
                            and the closest wcc at neighbouring strings
        max_iter:           max. number of iterations for 1 string
        min_neighbour_dist  minimum distance between neighbours when doing
                            the neighbour checks
        use_pickle:         toggles use of pickle for saving
        num_strings:           number of strings at the beginning (should be 
                            >= 8 for good results)
        verbose:            toggles output printed
        """
        kwarguments = copy.copy(self._defaults)
        kwarguments.update(kwargs)
        # parse input variables
        self._no_iter = kwarguments['no_iter']
        self._no_neighbour_check = kwarguments['no_neighbour_check']
        self._wcc_tol = kwarguments['wcc_tol']
        self._gap_tol = kwarguments['gap_tol']
        self._max_iter = kwarguments['max_iter']
        self._min_neighbour_dist = kwarguments['min_neighbour_dist']
        self._use_pickle = kwarguments['use_pickle']
        self._num_strings = kwarguments['num_strings']
        self._verbose = kwarguments['verbose']
            
        # checking num_strings
        if(self._num_strings < 2):
            raise ValueError("num_strings must be at least 2")
        elif(self._num_strings < 8):
            warnings.warn("num_strings should usually be >= 8 for good results", UserWarning)

        # initial output 
        if(self._verbose):
            string = "starting wcc calculation\n\n"
            length = max(len(key) for key in kwarguments.keys()) + 2
            for key in sorted(kwarguments.keys()):
                string += key.ljust(length) + str(kwarguments[key]) + '\n'
            string = string[:-1]
            print(string_tools.cbox(string))
            
        start_time = time.time()

        # initialising
        self._k_points = list(np.linspace(0, 0.5, self._num_strings, endpoint = True))
        self._gaps = [None for i in range(self._num_strings)]
        self._wcc_list = [[] for i in range(self._num_strings)] 
        self._neighbour_check = [False for i in range(self._num_strings - 1)]
        self._string_status = [False for i in range(self._num_strings)]
        
                
        # main calculation part
        # all neighbour checks can be true even if it did not converge!
        # a failed convergence (reaching lower limit) also produces
        # 'true'
        while not (all(self._neighbour_check)):
            for i, kx in enumerate(self._k_points):
                if not(self._string_status[i]):
                    self._wcc_list[i] = self._getwcc(kx)
                    self._gaps[i] = self._gapfind(self._wcc_list[i])
                    self._string_status[i] = True
                    self._save()
                    
            if not(self._no_neighbour_check):
                self._check_neighbours()
            else:
                if(self._verbose):
                    print('skipping neighbour checks')
                    break

        # dump results into pickle file
        self._save()
            
            
        # output to signal end of wcc calculation
        end_time = time.time()
        duration = end_time - start_time
        duration_string =   str(int(np.floor(duration / 3600))) + \
                            " h " + \
                            str(int(np.floor(duration / 60)) % 60) + \
                             " min " + \
                            str(int(np.floor(duration)) % 60) + \
                            " sec"
        if(self._verbose):
            print(string_tools.cbox( "finished wcc calculation" + "\ntime: " 
                            + duration_string))
        
        # return value
        return (self._k_points, self._wcc_list, self._gaps)
            
    #-------------------------------------------------------------------#
    #                support functions for wcc                          #
    #-------------------------------------------------------------------#

    # checking distance gap-wcc
    def _check_neighbours(self):
        """
        checks the neighbour conditions, adds a value in k_points when
        they are not fulfilled
        - adds at most one k_point per run
        - returns Boolean: all neighbour conditions fulfilled <=> True
        """
        for i, status in enumerate(self._neighbour_check):
            if not(status):
                if(self._string_status[i] and self._string_status[i + 1]):
                    if(self._verbose):
                        print("Checking neighbouring k-points k = " + "%.4f" % self._k_points[i] + " and k = " + "%.4f" % self._k_points[i + 1] + "\n", end = "")
                        sys.stdout.flush()
                    if(self._check_single_neighbour(i, i + 1)):
                        if(self._verbose):
                            print("Condition fulfilled\n\n", end = "")
                            sys.stdout.flush()
                        self._neighbour_check[i] = True
                    else:
                        if(self._k_points[i + 1] - self._k_points[i] < self._min_neighbour_dist):
                            if(self._verbose):
                                print("Reched minimum distance between neighbours, did not converge\n\n", end = "")
                                sys.stdout.flush()
                            self._neighbour_check[i] = True # convergence failed
                        else:
                            if(self._verbose):
                                print("Condition not fulfilled\n\n", end = "")
                                sys.stdout.flush()
                            # add entries to neighbour_check, k_point and string_status
                            self._neighbour_check.insert(i + 1, False)
                            self._string_status.insert(i + 1, False)
                            self._k_points.insert(i + 1, (self._k_points[i] + self._k_points[i+1]) / 2)
                            self._wcc_list.insert(i + 1, [])
                            self._gaps.insert(i + 1, None)
                            # check length of the variables
                            assert len(self._k_points) == len(self._wcc_list)
                            assert len(self._k_points) - 1 == len(self._neighbour_check)
                            assert len(self._k_points) == len(self._string_status)
                            assert len(self._k_points) == len(self._gaps)
                            return False
                else:
                    return False
        return True
    
    def _check_single_neighbour(self, i, j):
        """
        checks if the gap[i] is too close to any of the WCC in 
        wcc_list[j] and vice versa
        should be used with j = i + 1
        """
        return self._check_single_direction(self._wcc_list[j], self._gaps[i])
        
    def _check_single_direction(self, wcc, gap):
        """
        checks if gap is too close to any of the elements in wcc
        """
        for wcc_val in wcc:
            if(min(abs(1 + wcc_val - gap) % 1, abs(1 - gap + wcc_val) % 1) < self._gap_tol):
                return False
        return True
        
    # pickle: save and load
    def _save(self):
        """
        save k_points, wcc and gaps to pickle file
        only works if use_pickle = True & path to pickle_file exists
        """
        if(self._use_pickle):
            f = open(self._pickle_file, "wb")
            pickle.dump([self._k_points, self._wcc_list, self._gaps], f)
            f.close()
            
    def load(self):
        """
        load k_points, wcc and gaps from pickle file
        only works if pickle_file exists
        """
        f = open(self._pickle_file, "rb")
        [self._k_points, self._wcc_list, self._gaps] = pickle.load(f)
        f.close()
    
    # calculating one string
    def _getwcc(self, kx):
        """
        calculates WCC along a string by increasing the number of steps 
        (k-points) along the string until the WCC converge
        """
        # initial output
        if(self._verbose):
            print("calculating string at kx = " + "%.4f" % kx)
            sys.stdout.flush()

        # first two steps
        N = 8
        niter = 0
        if(self._verbose):
            print('    N = ' + str(N), end = '')
            sys.stdout.flush() # Output
        x, min_sv = self._trywcc(self._M_handle(kx, N))
        
        # no iteration
        if(self._no_iter):
            if(self._verbose):
                print('no iteration\n\n', end='')
                sys.stdout.flush()
        # iteration
        else:
            while(True):
                # larger steps for small min_sv (every second step)
                if(niter % 2 == 1 and min_sv < 0.5): 
                    N += 4
                else:
                    N += 2
                xold = copy.copy(x)
                if(self._verbose):
                    # Output
                    print("    N = " + str(N), end = "")
                    sys.stdout.flush()
                x, min_sv = self._trywcc(self._M_handle(kx, N))
                niter += 1

                # break conditions
                if(self._convcheck(x, xold)): # success
                    if(self._verbose):
                        print("finished!\n\n", end = "")
                        sys.stdout.flush()
                    break
                if(niter > self._max_iter): # failure
                    if(self._verbose):
                        print("failed to converge!\n\n", end = "")
                        sys.stdout.flush()
                    break
        return sorted(x)
    
    def _print_wcc(func):
        def inner(*args, **kwargs):
            res = func(*args, **kwargs)
            wcc = sorted(res[0])
            if(args[0]._verbose):
                print(" (" + "%.3f" % res[1] + ")", end = '\n        ')
                print('WCC positions: ' , end = '\n        ')
                print('[', end='')
                line_length = 0
                for i, val in enumerate(wcc[:-1]):
                    line_length += len(str(val)) + 2
                    if(line_length > 60):
                        print('', end = '\n        ')
                        line_length = len(str(val)) + 2
                    print(val, end = ', ')
                line_length += len(str(wcc[-1])) + 2
                if(line_length > 60):
                    print('', end = '\n        ')
                print(wcc[-1], end=']\n')
                sys.stdout.flush
            return res
        return inner
    
    @_print_wcc
    def _trywcc(self, allM):
        """
        Calculates the WCC from the MMN matrices
        """
        Gamma = np.eye(len(allM[0]))
        min_sv = 1
        for M in allM:
            [V,E,W] = la.svd(M)
            Gamma = np.dot(np.dot(V,W).conjugate().transpose(), Gamma)
            min_sv = min(min(E), min_sv)
        # getting the wcc from the eigenvalues of gamma
        [eigs, _] = la.eig(Gamma)
        return [(1j * np.log(z) / (2 * np.pi)).real % 1 for z in eigs], min_sv
    

        
    # wcc convergence functions
    def _convcheck(self, x, y):
        """
        check convergence of wcc from x to y
        
        depends on: self._wcc_tol
                    roughly corresponds to the total 'movement' in WCC that
                    is tolerated between x and y
        """
        if(len(x) != len(y)):
            if(self._verbose):
                print("Warning: consecutive strings don't have the same amount of WCC")
            return False
        else:
            return self._convsum(x, y, self._wcc_tol) < 1 

    def _convsum(self, listA, listB, epsilon = 1e-2, N0 = 7):
        """
        helper function for _convcheck
        
        calculates the absolute value of the change in density from listA
        to listB, when each WCC corresponds to a triangle of width epsilon
        (and total density = 1)
        """
        N = N0 * int(1/(2 * epsilon))
        val = np.zeros(N)
        for x in listA:
            index = int(N*x)
            for i in range(0, N0):
                val[(index - i) % N] += 1 - (i/N0)
            for i in range(1, N0):
                val[(index + i) % N] += 1 - (i/N0)
        for x in listB:
            index = int(N*x)
            for i in range(0, N0):
                val[(index - i) % N] -= 1 - (i/N0)
            for i in range(1, N0):
                val[(index + i) % N] -= 1 - (i/N0)
        return sum(abs(val)) / N0
        
    def _gapfind(self, x):
        """
        finds the largest gap in vector x, modulo 1
        """
        x = sorted(x)
        gapsize = 0
        gappos = 0
        N = len(x)
        for i in range(0, N - 1):
            temp = x[i + 1] - x[i]
            if(temp > gapsize):
                gapsize = temp
                gappos = i
        temp = x[0] - x[-1] + 1
        if(temp > gapsize):
            gapsize = temp
            gappos = N - 1
        return (x[gappos] + gapsize / 2) % 1
    #----------------END OF SUPPORT FUNCTIONS---------------------------#        
    
    def plot(self, shift = 0, show = True, ax = None):
        """
        plot WCC and largest gaps (with a shift modulo 1)
        """
        shift = shift % 1
        if not ax:
            return_fig = True
            fig = plt.figure()
            ax = fig.add_subplot(111)
        else: 
            return_fig = False
        ax.set_ylim(0,1)
        ax.set_xlim(-0.01, 0.51)
        ax.plot(self._k_points, [(x + shift) % 1 for x in self._gaps], 'bD')
        # add plots with +/- 1 to ensure periodicity
        ax.plot(self._k_points, [(x + shift) % 1 + 1 for x in self._gaps], 'bD')
        ax.plot(self._k_points, [(x + shift) % 1 - 1 for x in self._gaps], 'bD')
        for i, kpt in enumerate(self._k_points):
            ax.plot([kpt] * len(self._wcc_list[i]), [(x + shift) % 1 for x in self._wcc_list[i]], "ro")
            # add plots with +/- 1 to ensure periodicity
            ax.plot([kpt] * len(self._wcc_list[i]), [(x + shift) % 1 + 1 for x in self._wcc_list[i]], "ro")
            ax.plot([kpt] * len(self._wcc_list[i]), [(x + shift) % 1 - 1 for x in self._wcc_list[i]], "ro")
        ax.set_xlabel(r'$k$')
        ax.set_ylabel(r'$x$', rotation = 'horizontal')
        if(show):
            plt.show()
        if return_fig:
            return fig
        
    def get_res(self):
        """
        returns (k - points used, wcc calculated , largest gaps)
        """
        try:
            return (self._k_points, self._wcc_list, self._gaps)
        except (NameError, AttributeError):
            raise RuntimeError('WCC not yet calculated')
        # for a potential Python3 - only version
        #~ except (NameError, AttributeError) as e:
            #~ raise RuntimeError('WCC not yet calculated') from e
    
    def invariant(self):
        """
        calculate the Z2 topological invariant
        """
        try:
            inv = 1
            for i in range(0, len(self._wcc_list)-1):
                for j in range(0, len(self._wcc_list[0])):
                    inv *= self._sgng(self._gaps[i], self._gaps[i+1], self._wcc_list[i+1][j])
            
            return 1 if inv == -1 else 0
        except (NameError, AttributeError):
            raise RuntimeError('WCC not yet calculated')
        #~ except (NameError, AttributeError) as e:
            #~ raise RuntimeError('WCC not yet calculated') from e

        
    #-------------------------------------------------------------------#
    #                support functions for invariants                   #
    #-------------------------------------------------------------------#
    def _sgng(self, z, zplus, x):
        """
        calculates the invariant between two WCC strings
        """
        return np.copysign(1,np.sin(2*np.pi*(zplus - z)) + np.sin(2*np.pi*(x-zplus)) + np.sin(2*np.pi*(z-x)))
    #----------------END SUPPORT FUNCTIONS FOR INVARIANTS---------------#
    


    
from . import fp
from . import tb
    

if __name__ == "__main__":
    print("z2pack.py")