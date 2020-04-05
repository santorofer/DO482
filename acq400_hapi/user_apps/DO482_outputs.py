
import MDSplus
import time
import math
import numpy as np
from MDSplus import Tree
import sys
import csv

def setTransitionTimes(treeName, nchan, delta):
    tree = Tree(treeName, -1, 'EDIT')
    print('Tree Name: ', treeName)
    
    nchan   = int(nchan)
    current = 0.0
    delta   = float(delta) # sec
    end     = 4.0  # sec

    times   = np.arange(current, end, delta)  
    times_series = tree.getNode('ACQ2106_482:TIMES')
    times_series.record = times

    tran_indexes1 = range(0, len(times), 3)
    tran_indexes2 = range(0, len(times), 2)
    transitions1=times[tran_indexes1]    
    transitions2=times[tran_indexes2]
    
    transitions=times[[fib_recursive(i) for i in range(10)]] #a fibonacci series of transition times, as an example.
    
    for i in range(nchan):
        do_chan = tree.getNode('ACQ2106_482:OUTPUT_%3.3d' % (i+1))
        if (i % 2) == 0:  #Even Channels            
            do_chan.record = transitions
        else:
            do_chan.record = transitions2

    tree.write()
    tree.close()

    STL(treeName, times, nchan)

def STL(treeName, times, nchan):
    print("set_stl starting")
    tree = Tree(treeName, -1)

    output_states = np.zeros((nchan, len(times)), dtype=int ) # Matrix of output states
    do_chan_bits  = [] # indexes where the times (t) and the transition times (tt) are the same
    do_chan_index = [] # collect indexes where the t and tt are the same, for all the channels
    do_index      = []
    states_hex    = []
    states_bits   = []
    times_node = times

    for i in range(nchan):
        # DO_chan contains the transition times saved in the DO482:OUTPUT_xxx node
        do_chan = tree.getNode('ACQ2106_482:OUTPUT_%3.3d' % (i+1))
        do_chan_bits.append(np.zeros((len(do_chan.data()),), dtype=int))
            
        # Look for the indexes in the time series where the transitions are.
        for element in do_chan.data():
            do_chan_index.append(np.where(times_node == element))
        do_index.append(do_chan_index)
        do_chan_index = []


    for i in range(nchan):
        do_chan_bits[i][::2]=int(1) #a 1 or a 0 is associated to each of the transition times

        # Then, a state matrix is built. For each channel (a row in the matrix), the values from "do_chan_bits" are
        # place in the positions of the full time series:
        for j in range(len(do_index[i])):
            output_states[i][do_index[i][j]] = do_chan_bits[i][j]

        # Building the digital wave functions, and add them into the following node:
        #dwf_chan = tree.getNode('ACQ2106_482:OUTWF_%3.3d' % (i+1))
        #dwf_chan.record = output_states[i]
    print(output_states)
    
    for column in output_states.transpose():
        binstr = ''
        for element in column:
            binstr += str(element)
        states_bits.append(binstr)
    
    print(states_bits)

    for elements in states_bits:
        states_hex.append(hex(int(elements,2))[2:]) # the [2:] is because I don't need to 0x part of the hex string

    times_usecs = []
    for elements in times_node:
        times_usecs.append(int(elements * 1E6)) #in micro-seconds
    state_list = zip(times_usecs, states_hex)

    stlpath = '/home/fsantoro/HtsDevice/acq400_hapi/user_apps/STL/do_states.stl'
    outputFile=open(stlpath, 'w')

    with outputFile as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerows(state_list)

    outputFile.close()
    print("set_stl done")

def fib_recursive(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib_recursive(n-1) + fib_recursive(n-2)

if __name__ == '__main__':
    print('argument ',sys.argv[1])
    setTransitionTimes(sys.argv[1], sys.argv[2], sys.argv[3])
