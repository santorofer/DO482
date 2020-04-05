#
# Copyright (c) 2017, Massachusetts Institute of Technology All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice, this
# list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import MDSplus
import threading
from queue import Queue, Empty
import time
import socket
import math
import numpy as np
import csv

try:
    print('Imporing acq400_hapi: starting')
    acq400_hapi = __import__('acq400_hapi', globals(), level=1)
    print('Importing acq400_hapi: done')
except:
    acq400_hapi = __import__('acq400_hapi', globals())

class _ACQ2106_423ST_DIO482(MDSplus.Device):
    """
    D-Tacq ACQ2106 with ACQ423 Digitizers (up to 6)  real time streaming support.

    32 Channels * number of slots
    Minimum 2Khz Operation
    24 bits == +-10V

    3 trigger modes:
      Automatic - starts recording on arm
      Soft - starts recording on trigger method (reboot / configuration required to switch )
      Hard - starts recording on hardware trigger input

    Software sample decimation

    Settable segment length in number of samples

    debugging() - is debugging enabled.  Controlled by environment variable DEBUG_DEVICES

    """

    carrier_parts=[
        {'path':':NODE',        'type':'text',                     'options':('no_write_shot',)},
        {'path':':COMMENT',     'type':'text',                     'options':('no_write_shot',)},
        {'path':':TRIGGER',     'type':'numeric', 'value': 0.0,    'options':('no_write_shot',)},
        {'path':':TRIG_MODE',   'type':'text',    'value': 'hard', 'options':('no_write_shot',)},
        {'path':':EXT_CLOCK',   'type':'axis',                     'options':('no_write_shot',)},
        {'path':':FREQ',        'type':'numeric', 'value': 16000,  'options':('no_write_shot',)},
        {'path':':DEF_DECIMATE','type':'numeric', 'value': 1,      'options':('no_write_shot',)},
        {'path':':SEG_LENGTH',  'type':'numeric', 'value': 8000,   'options':('no_write_shot',)},
        {'path':':MAX_SEGMENTS','type':'numeric', 'value': 1000,   'options':('no_write_shot',)},
        {'path':':SEG_EVENT',   'type':'text',   'value': 'STREAM','options':('no_write_shot',)},
        {'path':':TRIG_TIME',   'type':'numeric',                  'options':('write_shot',)},
        {'path':':TRIG_STR',    'type':'text',   'valueExpr':"EXT_FUNCTION(None,'ctime',head.TRIG_TIME)",'options':('nowrite_shot',)},
        {'path':':RUNNING',     'type':'numeric',                  'options':('no_write_model',)},
        {'path':':LOG_FILE',    'type':'text',   'options':('write_once',)},
        {'path':':LOG_OUTPUT',  'type':'text',   'options':('no_write_model', 'write_once', 'write_shot',)},
        {'path':':INIT_ACTION', 'type':'action', 'valueExpr':"Action(Dispatch('CAMAC_SERVER','INIT',50,None),Method(None,'INIT',head))",'options':('no_write_shot',)},
        {'path':':STOP_ACTION', 'type':'action', 'valueExpr':"Action(Dispatch('CAMAC_SERVER','STORE',50,None),Method(None,'STOP',head))",      'options':('no_write_shot',)},
        {'path':':WRTD_EVENT', 'type': 'NUMERIC', 'options':('no_write_shot',)},
        {'path':':WRTD_TIME' , 'type': 'NUMERIC'   , 'options':('no_write_shot',)},
        {'path':':STL_FILE',   'type':'TEXT'},
        {'path':':TIMES',      'type': 'NUMERIC', 'options':('no_write_shot',)},
    ]

    data_socket = -1

    trig_types=[ 'hard', 'soft', 'automatic']

    def init(self):
        print('Init: starting')
        uut = acq400_hapi.Acq400(self.node.data(), monitor=False)
        print('uut ready')

        #Create the STL table from a series of transition times.
        self.set_stl()
        
        #Load the STL into the WRPG hardware: GPG
        traces = True
        self.load_stl_file(traces)
        print('WRPG has loaded the STL')
      
    INIT=init


    def load_stl_file(self,traces):
        example_stl=self.stl_file.data()    
        
        print('Path to State Table: ', example_stl)
        uut = acq400_hapi.Acq400(self.node.data(), monitor=False)
        uut.s0.trace = traces
        
        print('Loading STL table into WRPG')
        with open(example_stl, 'r') as fp:
            uut.load_wrpg(fp.read(), uut.s0.trace)

    def set_stl(self):
        print("set_stl starting")
        nchan = 32
        tree = Tree(treeName, -1)

        output_states = np.zeros((nchan, len(self.times.data())), dtype=int ) # Matrix of output states
        t_times_bits  = [] # the elements are the transition bits, 1s or 0s, for each channel.
        t_times_index = [] # collect indexes where the t and tt are the same, for all the channels

        states_hex    = []
        states_bits   = []

        times_node = self.times.data()

        for i in range(nchan):
            # t_times contains the transition times saved in the DO482:OUTPUT_xxx node        
            t_times = self.__getattr__('ACQ2106_482:OUTPUT_%3.3d' % (i+1))
            t_times_bits.append(np.zeros((len(t_times.data()),), dtype=int))
                
            # Look for the indexes in the time series where the transitions are.
            for element in t_times.data():
                t_times_index.append(np.where(times_node == element))

            t_times_bits[i][::2]=int(1) #a 1 or a 0 is associated to each of the transition times

            # Then, a state matrix is built. For each channel (a row in the matrix), the values from "t_times_bits" are
            # place in the positions of the full time series:
            for j in range(len(t_times_index)):
                output_states[i][t_times_index[j]] = t_times_bits[i][j]

            # Building the digital wave functions, and add them into the following node:
            dwf_chan = self.__getattr__('ACQ2106_482:OUTWF_%3.3d' % (i+1))
            dwf_chan.record = output_states[i]

            t_times_index = [] # re-initialize to startover for the next channel.

        print(output_states)

        for row in output_states.transpose():
            binstr = ''
            for element in row:
                binstr += str(element)
            states_bits.append(binstr)

        print(states_bits)

        for elements in states_bits:
            states_hex.append(hex(int(elements,2))[2:]) # the [2:] is because I don't need to 0x part of the hex string

        times_usecs = []
        for elements in times_node:
            times_usecs.append(int(elements * 1E6)) #in micro-seconds
        state_list = zip(times_usecs, states_hex)

        #stlpath = '/home/fsantoro/HtsDevice/acq400_hapi/user_apps/STL/do_states.stl'
        outputFile=open(self.stl_file.data(), 'w')

        with outputFile as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(state_list)

        outputFile.close()
        print("set_stl done")




def assemble(cls):
    cls.parts = list(_ACQ2106_423ST_DIO482.carrier_parts)

    for j in range(32):
        cls.parts += [
            {'path':':OUTPUT_%3.3d' % (j+1,),         'type':'NUMERIC', 'options':('no_write_shot',)},
            {'path':':OUTWF_%3.3d' % (j+1,),          'type':'NUMERIC', 'options':('no_write_model',)},
        ]

class ACQ2106_423_482_1ST(_ACQ2106_423ST_DIO482): sites=1
assemble(ACQ2106_423_482_1ST)
class ACQ2106_423_482_2ST(_ACQ2106_423ST_DIO482): sites=2
assemble(ACQ2106_423_482_2ST)
class ACQ2106_423_482_3ST(_ACQ2106_423ST_DIO482): sites=3
assemble(ACQ2106_423_482_3ST)
class ACQ2106_423_482_4ST(_ACQ2106_423ST_DIO482): sites=4
assemble(ACQ2106_423_482_4ST)
class ACQ2106_423_482_5ST(_ACQ2106_423ST_DIO482): sites=5
assemble(ACQ2106_423_482_5ST)

del(assemble)