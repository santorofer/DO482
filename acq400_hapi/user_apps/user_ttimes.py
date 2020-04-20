# A self contained unit test to create an STL table from a user's defined time series.
# Inputs:
# treeName: Name of the MDSplus tree
# nchan: # of channels used in the ACQ
# delta: a delta time to build a series of time to choose from
# stlpath: path to where the STL file will reside, for example:
# stlpath = '/home/fsantoro/HtsDevice/acq400_hapi/user_apps/STL/do_states.stl'
# The file name should have an extension called: .stl
#
# Output: the STL file. Eg. do_states.stl
#
# Usage:
# python3 ~/HtsDevice//acq400_hapi/user_apps/user_ttimes.py daqtest 32 1 "/home/fsantoro/HtsDevice/acq400_hapi/user_apps/STL/do_states.stl"



import MDSplus
import time
import math
import numpy as np
from MDSplus import Tree
import sys
import csv
import copy

def setTransitionTimes(treeName, nchan, delta, stlpath):
    #This function is kind of a Unit Test.

    tree = Tree(treeName, -1, 'EDIT')
    print('Tree Name: ', treeName)

    nchan   = int(nchan)
    current = 0.0
    delta   = float(delta) # sec
    end     = 40.0  # sec

    times   = np.arange(current, end, delta)

    transitions1 = np.array([
                            [times[1],int(0)], [times[2],int(1)],
                            [times[3],int(0)], [times[4],int(1)],[times[5],int(0)],
                            [times[6],int(1)], [times[8],int(1)],
                            [times[9],int(1)], [times[10],int(0)], [times[11],int(1)],
                            [times[12],int(0)], [times[13],int(1)], [times[14],int(0)],
                            [times[15],int(1)], [times[16],int(0)], [times[17],int(1)],
                            [times[18],int(0)], [times[19],int(1)], [times[30],int(0)]]
                            )

    transitions2 = np.array([[times[0],int(0)],[times[3],int(1)], [times[7],int(0)]])


    for i in range(nchan):
        t_times = tree.getNode('ACQ2106_WRPG:OUTPUT_%3.3d' % (i+1))

        if (i % 2) == 0:  #Even Channels
            t_times.record = transitions1
        else:
            t_times.record = transitions2

    tree.write()
    tree.close()

    set_stl(treeName, times, nchan, stlpath)

def set_stl(treeName, times, nchan, stlpath):
    tree = Tree(treeName, -1)
    states_hex    = []
    states_bits   = []
    all_t_times   = []
    all_t_times_states = []

    for i in range(nchan):
        chan_t_times = tree.getNode('ACQ2106_WRPG:OUTPUT_%3.3d' % (i+1))

        # Pair of (transition time, state) for each channel:
        chan_t_states = chan_t_times.data()

        # Creation of an array that contains as EVERY OTHER element all the transition times in it, adding them
        # for each channel:
        for x in np.nditer(chan_t_states):
            all_t_times_states.append(x) #Appends arrays made of one element,

    # Choosing only the transition times:
    all_t_times = all_t_times_states[0::2]

    # Removing duplicates and then sorting in ascending manner:
    t_times = []
    for i in all_t_times:
       if i not in t_times:
          t_times.append(i)

    # t_times contains the unique set of transitions times used in the experiment:
    t_times = sorted(np.float64(t_times))
    print(t_times)

    # initialize the state matrix
    rows, cols = (len(t_times), nchan)
    state = [[0 for i in range(cols)] for j in range(rows)]


    # Building the state matrix. For each transition times given by t_times, we look for those times that
    # appear in the channel. If a transition time does not appear in that channel, then the state
    # doesn't change.
    for j in range(nchan):
        chan_t_states = tree.getNode('ACQ2106_WRPG:OUTPUT_%3.3d' % (j+1))
        for i in range(len(t_times)):
            #print(j, i, state[i][j])     
            if i == 0:
                state[i][j] = 0
            else:
                state[i][j] = state[i-1][j]
                
                # chan_t_states its elements are pairs of [ttimes, state]. e.g [[0.0, 0],[1.0, 1],...]
                # chan_t_states[0] are all the first elements of those pairs, i.e the trans. times: e.g [[1D0], [2D0], [3D0], [4D0] ... ]
                # chan_t_states[1] are all the second elements of those pairs, the states: .e.g [[0],[1],...]
                for t in range(len(chan_t_states[0])):
                    #Check if the transition time is one of the times that belongs to this channel:
                    if t_times[i] == chan_t_states[0][t][0]:
                        #print("t_times is in chan ", int(chan_t_states[1][t][0]))
                        state[i][j] = int(chan_t_states[1][t][0])



    # Building the string of 1s and 0s for each transition time:
    binrows = []
    for row in state:
        rowstr = [str(i) for i in np.flip(row)]  
        binrows.append(''.join(rowstr))

    print(binrows)

    # Converting the original units of the transtion times in seconds, to micro-seconts:
    times_usecs = []
    for elements in t_times:
        times_usecs.append(int(elements * 1E6)) #in micro-seconds
    # Building a pair between the t_times and hex states:
    state_list = zip(times_usecs, binrows)

    f=open(stlpath, 'w')

    for s in state_list:
        f.write('%d,%08X\n' % (s[0], int(s[1], 2)))

    f.close()


if __name__ == '__main__':
    print('argument ',sys.argv[1])
    start_time = time.time()
    setTransitionTimes(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print("--- %s seconds ---" % (time.time() - start_time))


