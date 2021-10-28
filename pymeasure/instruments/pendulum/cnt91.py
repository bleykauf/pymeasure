#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2021 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
from time import sleep

from pymeasure.instruments import Instrument

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CNT91(Instrument):
    """Represents a Pendulum CNT91 frequency counter."""

    CHANNELS = {"A": 1, "B": 2, "C": 3, "REAR": 4, "INTREF": 6}
    TRIGGER_SOURCES = {
        "A": "EXT1",
        "B": "EXT2",
        "REAR": "EXT4",
    }
    MAX_N_SAMPLES = int(1e5)

    def __init__(self, resourceName, **kwargs):
        super().__init__(resourceName, "Pendulum CNT-91", **kwargs)
        self.adapter.connection.timeout = 120000

    def ask(self, cmd):
        response = super().ask(cmd).rstrip("\n")
        return response

    def read_buffer(self):
        """Read out the entire device buffer"""
        data = []

        # loop until the buffer was completely read out
        while True:
            new = [
                float(value) for value in self.ask(":FETC:ARR? MAX").split(",") if value
            ]
            data += new

            if len(new) < self.batch_size:
                break

        return data

    @property
    def batch_size(self):
        # how many entries of the buffer can be transmitted with one query?
        if not hasattr(self, "_batch_size"):
            self._batch_size = int(self.ask("FORM:SMAX?"))
        return self._batch_size

    def get_time_series(self, channel, n_samples, sample_rate, trigger_source=None):
        try:
            channel = self.CHANNELS[channel]
        except ValueError:
            raise Exception(
                "Invalid channel %s, valid values are %s"
                % (channel, list(self.CHANNELS.keys()))
            )

        measurement_time = 1 / sample_rate
        cmds = [
            # set output format to ascii
            "FORM ASC",
            # set channel number and number of repetitions
            ":CONF:ARR:FREQ %d,(@%d)" % (n_samples, channel),
            # disable continuous mode
            ":INIT:CONT OFF",
            # set measurement time
            ":ACQ:APER %f" % measurement_time,
        ]

        self.clear()

        self.write(";".join(cmds))

        if trigger_source:
            self.write(
                ["ARM:SOUR %s" % self.TRIGGER_SOURCES[trigger_source], "ARM:SLOP POS"]
            )

        # start the measurement (or wait for trigger)
        self.write(":INIT")

        return self.wait_and_return()

    @property
    def operation_complete(self):
        return self.ask("*OPC?") == "1"

    def wait_and_return(self):
        while not self.operation_complete:
            sleep(0.1)

        data = self.read_buffer()
        if len(data) == 1:
            return data[0]
        return data
