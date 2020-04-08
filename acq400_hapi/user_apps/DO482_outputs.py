
import MDSplus
import time
import math
import numpy as np
from MDSplus import Tree
import sys
import csv

def setTransitionTimes(treeName, nchan, delta):
    #This function is kind of a Unit Test.

    tree = Tree(treeName, -1, 'EDIT')
    print('Tree Name: ', treeName)

    nchan   = int(nchan)
    current = 0.0
    delta   = float(delta) # sec
    end     = 10.0  # sec

    times   = np.arange(current, end, delta)

    #Ex. 1
    # User selected (transtion times, states):
    transitions1 = np.array([[times[0],int(1)],[times[1],int(0)],[times[2],int(1)],[times[3],int(0)]])
    transitions2 = np.array([[times[1],int(1)],[times[3],int(0)]])

    for i in range(nchan):
        t_times = tree.getNode('ACQ2106_WRPG:OUTPUT_%3.3d' % (i+1))

        if (i % 2) == 0:  #Even Channels
            t_times.record = transitions1
        else:
            t_times.record = transitions2

    tree.write()
    tree.close()

    #STL(treeName, times, nchan)
    set_stl(treeName, times, nchan)

def set_stl(treeName, times, nchan):
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
    state = [[0]*cols]*rows

    # Building the state matrix. For each transition times given by t_times, we look for those that
    # appear in the channel. If a transition time does not appear in that channel, then the state
    # for this transition time is consider the same as the previous state for this channel (i.e. the state
    # hasn't changed)
    i=0
    for t in t_times:
        print(i, state[i])     
        for j in range(nchan):
            chan_t_states = tree.getNode('ACQ2106_WRPG:OUTPUT_%3.3d' % (j+1))
            
            for s in range(len(chan_t_states[0])):
                #Check if the transition time is one of the times that belongs to this channel:
                if t in chan_t_states[0][s]:
                    print("inside Chan%i" %(j+1), t, i, j, int(np.asscalar(chan_t_states[1][s])))
                    state[i][j] = int(np.asscalar(chan_t_states[1][s]))
            print("       Chan%i" %(j+1), t, i, j, state[i][j])

        # Building the string of 1s and 0s for each transition time:
        binstr = ''
        for element in state[i]:
            binstr += str(element)
        states_bits.append(binstr)
        
        i+=1

    print(states_bits)

    #Converting those strings into HEX numbers
    for elements in states_bits:
        states_hex.append(hex(int(elements,2))[2:]) # the [2:] is because I don't need to 0x part of the hex string

    # Converting the original units of the transtion times in seconds, to micro-seconts:
    times_usecs = []
    for elements in t_times:
        times_usecs.append(int(elements * 1E6)) #in micro-seconds
    # Building a pair between the t_times and hex states:
    state_list = zip(times_usecs, states_hex)

    stlpath = '/home/fsantoro/HtsDevice/acq400_hapi/user_apps/STL/do_states.stl'
    outputFile=open(stlpath, 'w')

    with outputFile as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerows(state_list)

    outputFile.close()


if __name__ == '__main__':
    print('argument ',sys.argv[1])
    setTransitionTimes(sys.argv[1], sys.argv[2], sys.argv[3])
