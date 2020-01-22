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
from MDSplus import Event,Range
import numpy as np
import csv

try:
    acq400_hapi = __import__('acq400_hapi', globals(), level=1)
except:
    acq400_hapi = __import__('acq400_hapi', globals())

class ACQ2106_DO482(MDSplus.Device):
    """
    D-Tacq ACQ2106 with DOI482.

    32 Channels * number of slots: Inputs or Outputs
    Minimum 2Khz Operation
    24 bits == +-10V

    3 trigger modes:
      Automatic - starts recording on arm
      Soft - starts recording on trigger method (reboot / configuration required to switch )
      Hard - starts recording on hardware trigger input

    debugging() - is debugging enabled.  Controlled by environment variable DEBUG_DEVICES

    """

    parts = [{'path': ':NODE', 'type': 'TEXT'   , 'options':('no_write_shot',)},
             {'path': ':COMMENT', 'type': 'TEXT'}  ,
             {'path': ':TRIGGER', 'type': 'NUMERIC', 'options':('no_write_shot',)},
             {'path': ':CLOCK'  , 'type': 'AXIS'   , 'options':('no_write_shot',)},
             {'path': ':SEG_EVENT',   'type':'text',   'value': 'TRANSIENT','options':('no_write_shot',)},
             {'path': ':WRTD_EVENT', 'type': 'NUMERIC', 'options':('no_write_shot',)},
             {'path': ':WRTD_TIME' , 'type': 'NUMERIC'   , 'options':('no_write_shot',)},
             {'path': ':RUNNING','type':'any', 'options':('no_write_model',)},
             {'path': ':STL_FILE','type':'TEXT'},
             {'path': ':TIMES', 'type': 'NUMERIC', 'options':('no_write_shot',)},
            ]

    for i in range(32):
        parts += [{'path': ":OUTPUT_%2.2d" % (i+1), 'type': 'NUMERIC', 'options':('write_once')}]
        parts += [{'path': ":OUTPUT_WF_%2.2d" % (i+1), 'type': 'NUMERIC', 'options':('write_once')}]

    debug=None

    trig_types=[ 'hard', 'soft', 'automatic']

    def init(self):
        uut = acq400_hapi.Acq400(self.node.data(), monitor=False)

        #Setting the trigger in the GPG module
        uut.s0.GPG_ENABLE   ='enable'
        uut.s0.GPG_TRG      ='enable'
        uut.s0.GPG_TRG_DX   ='d0'
        uut.s0.GPG_TRG_SENSE='rising'

        #Setting SYNC Main Timing Highway Source Routing --> White Rabbit Time Trigger
        uut.s0.SIG_SRC_TRG_0='WRTT'

        #Setting the trigger in ACQ2106 transient control
        uut.s1.TRG      ='enable'
        uut.s1.TRG_DX   ='d0'
        uut.s1.TRG_SENSE='rising'
        uut.s0.TRANSIENT_POST = '50000' #post number of samples

        self.running.on=True
        self.set_stl()
        self.run_wrpg()
        uut.s0.set_arm = '1'

        #Event.setevent(self.seg_event.data())

    INIT=init

    def stop(self):
        self.running.on = False
    STOP=stop

    def load_stl_file(self):
        uut = acq400_hapi.Acq400(self.node.data(), monitor=False)
        print('Path to State Table: ', self.stl_file.data())

        with open(self.stl_file.data(), 'r') as fp:
            uut.load_wrpg(fp.read(), uut.s0.trace)

    def run_wrpg(self):
        uut = acq400_hapi.Acq400(self.node.data(), monitor=False)
        self.load_stl_file()

    def set_stl(self):
        nchan = 32
        output_states = np.zeros((nchan, len(self.times.data())), dtype=int )
        do_chan_bits  = []
        do_chan_index = []
        do_index      = []
        states_bits   = []
        states_hex    = []
        #times_times_delta =[]
        #bits_flipbits     =[]

        times_node = self.times.data()

        for i in range(nchan):
            do_chan = self.__getattr__('OUTPUT_%2.2d' % (i+1))
            do_chan_bits.append(np.zeros((len(do_chan.data()),), dtype=int))
            #print(i, len(do_chan.data()), do_chan.data())
 
            for element in do_chan.data():
                do_chan_index.append(np.where(times_node == element))
            do_index.append(do_chan_index)
            do_chan_index = []

            # times_times_delta.append(np.zeros((2*len(do_chan.data()))))
            # bits_flipbits.append(np.zeros((2*len(do_chan_bits[i]))))
            
        #for i in range(nchan):
        #    do_chan = self.__getattr__('OUTPUT_%2.2d' % (i+1))
        #
        #    deltatime   =1E-6 #usec
        #    times_delta =[]
        #    for elements in do_chan.data():
        #        times_delta.append(elements - deltatime)
        #    #print('times_delta:  ', times_delta)
        #    #print('do_chan.data ', do_chan.data())
        #
        #    times_times_delta[i][1::2] = np.array(do_chan.data())
        #    times_times_delta[i][0::2] = np.array(times_delta)   
        #    #print('all times ', times_times_delta[i])
 
        for i in range(nchan):
            do_chan_bits[i][::2]=int(1) #a 1 or a 0 is associated to each of the transition times
   
            # Then, a state matrix is built. For each channel (a line in the matrix), the values from "do_chan_bits" are
            # added to the full time series:
            for j in range(len(do_index[i])):
                output_states[i][do_index[i][j]] = do_chan_bits[i][j]
            
            #print('Transitions per channel: ', i, output_states[i])
            
            # Building the digital wave functions, and add them into the following node:
            dwf_chan = self.__getattr__('OUTPUT_WF_%2.2d' % (i+1))
            
            flipbits = []
            for element in do_chan_bits[i]:
                if element == int(1):
                    flipbits.append(int(0))
                else:
                    flipbits.append(int(1))
            
            #bits_flipbits[i][1::2] = do_chan_bits[i]
            #bits_flipbits[i][0::2] = flipbits
            #
            dwf_chan.record = output_states[i]
 
        for column in output_states.transpose():
            binstr = ''
            for element in column:
                binstr += str(element)
            states_bits.append(binstr)

        for elements in states_bits:
            states_hex.append(hex(int(elements,2))[2:]) # the [2:] is because I don't need to 0x part of the hex string

        times_usecs = []
        for elements in times_node:
            times_usecs.append(int(elements * 1E6))
        state_list = zip(times_usecs, states_hex)

        #stlpath = '/home/fsantoro/HtsDevice/acq400_hapi/user_apps/STL/do_states.stl'
        outputFile=open(self.stl_file.data(), 'w')

        with outputFile  as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(state_list)

        outputFile.close()

