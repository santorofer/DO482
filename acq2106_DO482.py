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

    parts = [{'path': ':ADDRESS', 'type': 'TEXT'   , 'options':('no_write_shot',)},
             {'path': ':COMMENT', 'type': 'TEXT'}  ,
             {'path': ':TRIGGER', 'type': 'NUMERIC', 'options':('no_write_shot',)},
             {'path': ':CLOCK'  , 'type': 'AXIS'   , 'options':('no_write_shot',)},
             {'path': ':WRTD_EVENT', 'type': 'NUMERIC', 'options':('no_write_shot',)},
             {'path': ':WRTD_TIME' , 'type': 'NUMERIC'   , 'options':('no_write_shot',)},
             {'path': ':RUNNING','type':'any', 'options':('no_write_model',)},
             {'path': ':STL_FILE','type':'TEXT'},
            ]

    for i in range(32):
        parts += [{'path': ":OUTPUT_%2.2d" % (i+1), 'type': 'NUMERIC', 'options':('write_once')}]
        parts += [{'path': ":OUTPUT_WF_%2.2d" % (i+1), 'type': 'NUMERIC', 'options':('write_once')}]

    debug=None

    trig_types=[ 'hard', 'soft', 'automatic']

    def init(self):
        self.uut = acq400_hapi.Acq400(self.address.data(), monitor=False)
       
        #Setting the trigger in the GPG module
        self.uut.s0.GPG_ENABLE   ='enable'
        self.uut.s0.GPG_TRG      ='external'
        self.uut.s0.GPG_TRG_DX   ='d0'
        self.uut.s0.GPG_TRG_SENSE='rising'

        #Setting SYNC Main Timing Highway Source Routing --> White Rabbit Time Trigger
        self.uut.s0.SIG_SRC_TRG_0='WRTT'

        #Setting the trigger in ACQ2106 transient control
        self.uut.s1.TRG      ='enable'
        self.uut.s1.TRG_DX   ='d0'
        self.uut.s1.TRG_SENSE='rising'
        self.uut.s0.TRANSIENT_POST = '100000' #post number of samples

        self.running.on=True
        self.run_wrpg()

    INIT=init

    def stop(self):
        self.running.on = False
    STOP=stop

    def load_stl_file(self):
        stl_file_path = self.stl_file.data()
        print(stl_file_path)

        with open(stl_file_path, 'r') as fp:
            self.uut.load_wrpg(fp.read(), self.uut.s0.trace)

    def run_wrpg(self):
        self.load_stl_file()
        self.uut.s0.set_arm = '1'

