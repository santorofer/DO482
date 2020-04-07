
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
    end     = 10.0  # sec

    times   = np.arange(current, end, delta)  
    times_series = tree.getNode('ACQ2106_WRPG:TIMES')
    times_series.record = times

    tran_indexes1 = range(0, len(times), 5)
    tran_indexes2 = range(0, len(times), 2)
    transitions1=times[tran_indexes1]    
    transitions2=times[tran_indexes2]
    
    transitions=times[[fib_recursive(i) for i in range(10)]] #a fibonacci series of transition times, as an example.
    
    for i in range(nchan):
        t_times = tree.getNode('ACQ2106_WRPG:OUTPUT_%3.3d' % (i+1))
        # t_times.record = transitions1

        if (i % 2) == 0:  #Even Channels            
            t_times.record = transitions1
        else:
            t_times.record = transitions1

    tree.write()
    tree.close()

    STL(treeName, times, nchan)

def STL(treeName, times, nchan):
    print("set_stl starting")
    tree = Tree(treeName, -1)

    all_t_times = []
    t_times_bits  = [] # the elements are the transition bits, 1s or 0s, for each channel.
    chan_bits = []

    states_hex    = []
    states_bits   = []

    for i in range(nchan):
        # chan_t_times contains the transition times saved in the DO482:OUTPUT_xxx node        
        chan_t_times = tree.getNode('ACQ2106_WRPG:OUTPUT_%3.3d' % (i+1))
        chan_bits.append(np.zeros((len(chan_t_times.data()),), dtype=int))
        
        all_t_times.extend(chan_t_times)
        chan_bits[i][::2]=int(1)

        t_times_bits.append(merge(chan_t_times.data(),chan_bits[i]))

        # Building the digital wave functions, and add them into the following node:
        #dwf_chan = tree.getNode('ACQ2106_482:OUTWF_%3.3d' % (i+1))
        #dwf_chan.record = output_states[i]

    t_times = []
    for i in all_t_times:
       if i not in t_times:
          t_times.append(i)

    #t_times = sorted(set(t_times))
    t_times_bits_flat = [item for sublist in t_times_bits for item in sublist]

    print(sorted(t_times))
    t_times = sorted(t_times)

    for element in t_times:
        same_t_times = [item for item in t_times_bits_flat 
              if item[0] == element]
        print(same_t_times)
        n = 1 # N. . .
        bins = [x[n] for x in same_t_times]
        print(bins)

        binstr = ''
        for element in bins:
            binstr += str(element)
        states_bits.append(binstr)
    
    for elements in states_bits:
        states_hex.append(hex(int(elements,2))[2:]) # the [2:] is because I don't need to 0x part of the hex string

    times_usecs = []
    for elements in t_times:
        times_usecs.append(int(elements * 1E6)) #in micro-seconds
    state_list = zip(times_usecs, states_hex)

    stlpath = '/home/fsantoro/HtsDevice/acq400_hapi/user_apps/STL/do_states.stl'
    outputFile=open(stlpath, 'w')

    with outputFile as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerows(state_list)

    outputFile.close()
    print("set_stl done")

def merge(list1, list2): 
    merged_list = [(list1[i], list2[i]) for i in range(0, len(list1))] 
    return merged_list

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
