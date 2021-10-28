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
from pymeasure.instruments.validators import strict_discrete_range

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
    MAX_SAMPLE_RATE = 1e5

    def __init__(self, resourceName, **kwargs):
        super().__init__(resourceName, "Pendulum CNT-91", **kwargs)
        self.adapter.connection.timeout = 120000

    def ask(self, cmd):
        response = super().ask(cmd).rstrip("\n")
        return response

    @property
    def operation_complete(self):
        """Is True if operation is complete."""
        return self.ask("*OPC?") == "1"

    @property
    def batch_size(self):
        """Maximum number of buffer entries that can be transmitted at once."""
        if not hasattr(self, "_batch_size"):
            self._batch_size = int(self.ask("FORM:SMAX?"))
        return self._batch_size

    def read_buffer(self):
        """
        Read out the entire device buffer one value at a time.

        :yield : Frequency values from the buffer
        """
        data = []

        # loop until the buffer was completely read out
        while True:

            # get maximum number of buffer values
            data = [float(x) for x in self.ask(":FETC:ARR? MAX").split(",")]

            for value in data:
                # only yield single values to play nice with pymeausre's
                # Procedures
                yield value

            # last values has been read from buffer
            if len(data) < self.batch_size:
                break

    def arm_trigger_source(self, trigger_source):
        """
        Arm a trigger source.

        param trigger_source : The channel on which the trigger is set.
        """
        assert trigger_source in self.TRIGGER_SOURCES.keys()

        trigger_source = self.TRIGGER_SOURCES[trigger_source]
        self.write(f"ARM:SOUR {trigger_source}; ARM:SLOP POS")

    def set_measurement_time(self, measurement_time):
        self.write(f":ACQ:APER {measurement_time}")

    format = Instrument.control(
        "FORM?",
        "FORM %s",
        "Reponse format (ASCII or REAL)",
        validator=strict_discrete_range,
        values=["ASCII", "REAL"]
        )

    def configure_array_measurement(self, n_samples, channel):
        """
        Configure the counter for an array of measurements.
        """
        assert n_samples <= self.MAX_N_SAMPLES
        channel = self.CHANNELS[channel]
        self.write(f":CONF:ARR:FREQ {n_samples},(@{channel})")

    def buffer_time_series(
            self,
            channel,
            n_samples,
            sample_rate,
            trigger_source=None):
        """
        Record a time series to the buffer and read it out after completion.

        :param channel: Channel that should be used.
        :param n_samples : The number of samples
        :param sample_rate : Sample rate in Hz.
        :param trigger_source: Optionally specify a trigger source to start the
                               measurement.
        """

        assert sample_rate <= self.MAX_SAMPLE_RATE

        measurement_time = 1 / sample_rate
        cmds = [
            ":INIT:CONT OFF",
        ]

        self.clear()        
        self.format("ASCII")
        self.configure_array_measurement(n_samples, channel)
        self.write(";".join(cmds))
        self.set_measurement_time(measurement_time)

        if trigger_source:
            self.arm_trigger_source(trigger_source)

        # start the measurement (or wait for trigger)
        self.write(":INIT")

        while not self.operation_complete:
            sleep(0.01)
