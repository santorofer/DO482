
import MDSplus
import time
import math
import numpy as np
from MDSplus import Tree
import sys
import csv

def setOutputTimes(treeName, nchan, delta):
    tree = Tree(treeName, -1, 'EDIT')
    print('Tree Name: ', treeName)
    
    nchan   = int(nchan)
    current = 0.0
    delta   = float(delta) # sec
    end     = 4.0  # sec

    times   = np.arange(current, end, delta)  
    times_series = tree.getNode('DO482:TIMES')
    times_series.record = times

    tran_indexes1 = range(0, len(times), 3)
    tran_indexes2 = range(0, len(times), 2)
    transitions1=times[tran_indexes1]    
    transitions2=times[tran_indexes2]
    
    transitions=times[[fib_recursive(i) for i in range(10)]] #a fibonacci series of transition times, as an example.
    
    for i in range(nchan):
        do_chan = tree.getNode('DO482:OUTPUT_%2.2d' % (i+1))
        if (i % 2) == 0:  #Even Channels            
            do_chan.record = transitions
        else:
            do_chan.record = transitions2

    tree.write()
    tree.close()

    #STL(treeName, times, nchan)

def STL(treeName, times, nchan):

    tree = Tree(treeName, -1)
    output_states = np.zeros((nchan, len(times)), dtype=int )
    do_chan_bits  = []
    do_chan_index = []
    do_index      = []
    states_bits   = []
    states_hex    = []

    for i in range(nchan):
        do_chan = tree.getNode('DO482:OUTPUT_%2.2d' % (i+1))
        do_chan_bits.append(np.zeros((len(do_chan.data()),), dtype=int))
        
        for element in do_chan.data():
            do_chan_index.append(np.where(times == element))
        do_index.append(do_chan_index)
        do_chan_index = []
        
        #print(do_index[i])
  
    for i in range(nchan):
        do_chan_bits[i][::2]=int(1)
        
        for j in range(len(do_index[i])):
            output_states[i][do_index[i][j]] = do_chan_bits[i][j]
        
        print('Transitions per channel: ', i, output_states[i]) 

    for column in output_states.transpose():
        binstr = ''
        for element in column:
            binstr += str(element)
        states_bits.append(binstr)
        
    for elements in states_bits:
        #print(elements, hex(int(elements,2))[2:])
        states_hex.append(hex(int(elements,2))[2:]) # the [2:] is because I don't need to 0x part of the hex string

    usecs = []
    for elements in times:
        usecs.append(int(elements * 1E6))
    state_list = zip(usecs, states_hex)
    
    stlpath = '/home/fsantoro/HtsDevice/acq400_hapi/user_apps/STL/do_states.stl'
    outputFile=open(stlpath, 'w')

    with outputFile  as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerows(state_list)
    
    outputFile.close()

def fib_recursive(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib_recursive(n-1) + fib_recursive(n-2)

if __name__ == '__main__':
    print('argument ',sys.argv[1])
    setOutputTimes(sys.argv[1], sys.argv[2], sys.argv[3])
