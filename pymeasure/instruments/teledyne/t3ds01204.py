#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2022 PyMeasure Developers
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

import numpy as np
from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import (strict_discrete_set,
                                              truncated_discrete_set)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class T3DS01204(Instrument):
    """Represents a Teledyne T3DS01204 oscilloscope."""

    def __init__(self, resourceName, **kwargs):
        super().__init__(resourceName, "Teledyne T3DS01204", includeSCPI=True, **kwargs)
        # Make sure communication mode is off so queries are interpreted correctly.
        self._comm_header = "OFF"

    # COMM_HEADER commands -------------------------------------------------------------

    _comm_header = Instrument.control(
        "CHDR?",
        "CHDR  %s",
        "Controls the way the oscilloscope formats response to queries.",
        validator=strict_discrete_set,
        values=["OFF", "SHORT", "LONG"],
    )

    # ACQUIRE commands -----------------------------------------------------------------

    def arm_acquisition(self):
        """Start a new signal acquisition."""
        self.write("ARM")

    def stop(self):
        """
        Stop the current acquisition. This is the same as pressing the Stop key on the
        front panel.
        """
        self.write("STOP")

    sample_rate = Instrument.measurement("SARA?", "Sample rate of the scope")

    sample_number = Instrument.measurement(
        "SANU?",
        "The number of data points that the hardware will acquire from the input"
        "signal. The number of points acquired is based on the horizontal scale and"
        "memory/acquisition depth selections",
    )

    # AUTOSET commands -----------------------------------------------------------------

    def autoset(self):
        """
        Attempts to identify the waveform type and automatically adjusts controls to
        produce a usable display of the input signal.
        """
        self.write("ASET")

    # TIMEBASE commands ----------------------------------------------------------------
    time_div = Instrument.control(
        "TDIV?",
        "TDIV %s",
        "Horizontal scale in s/div",
        validator=truncated_discrete_set,
        values=[
            1e-9,
            2e-9,
            5e-9,
            10e-9,
            20e-9,
            50e-9,
            100e-9,
            200e-9,
            500e-9,
            1e-6,
            2e-6,
            5e-6,
            10e-6,
            20e-6,
            50e-6,
            100e-6,
            200e-6,
            500e-6,
            1e-3,
            2e-3,
            5e-3,
            10e-3,
            20e-3,
            50e-3,
            100e-3,
            200e-3,
            500e-3,
            1,
            2,
            5,
            10,
            20,
            50,
            100,
        ],
    )

    trigger_delay = Instrument.control(
        "TRDL?",
        "TRDL %s",
        "Time interval between trigger event and the horizontal center point in s.",
    )

    # TRIGGER commands -----------------------------------------------------------------

    def select_trigger(
        self,
        source,
        trigger_type="EDGE",
        hold_type="OFF",
        hold_value=None,
        hold_value2=None,
    ):
        """
        Select the condition that will trigger the acqusition of the waveforms.

        Depending on the trigger type, additional parameters must be specified. 
        """
        # checking for valid trigger type
        trigger_type = strict_discrete_set(
            trigger_type, ["EDGE", "SLEW", "GLIT", "INTV", "RUNT", "DROP"]
        )

        # checking for valid source
        if trigger_type == "EDGE":
            source = strict_discrete_set(source, [1, 2, 3, 4, "LINE", "EX", "EX5"])
        else:
            source = strict_discrete_set(source, [1, 2, 3, 4])
        # format source channel
        if type(source) == int:
            source = f"C{source}"

        # checking for valid hold type
        if trigger_type == "EDGE":
            hold_type = strict_discrete_set(hold_type, ["TI", "OFF"])
        elif trigger_type == "DROP":
            hold_type = strict_discrete_set(hold_type, ["TI"])
        elif trigger_type == "GLIT" or trigger_type == "RUNT":
            hold_type = strict_discrete_set(hold_type, ["PS", "PL", "P1", "P2"])
        elif trigger_type == "INTV" or hold_type == "SLEW":
            hold_type = strict_discrete_set(hold_type, ["IS", "IL", "I1", "I2"])

        # Building the command
        cmd = f"TRSE  {trigger_type},SR,{source},HT,{hold_type}"
        if not hold_type == "OFF":
            if not hold_value:
                raise ValueError(
                    "Hold_value must be specified when hold_type is not 'OFF'."
                )
            cmd += f",HV,{hold_value}"
            if hold_value2:
                cmd += f",HV2,{hold_value2}"
        self.write(cmd)

    def set_trigger_slope(self, source, slope):
        """
        Trigger slope of the specified trigger source.
        """
        source = strict_discrete_set(source, [1, 2, 3, 4, "EX", "EX5"])
        if type(source) == int:
            source = f"C{source}"
        slope = strict_discrete_set(slope, ["POS", "NEG", "WINDOW"])
        self.write(f"{source}:TRSL {slope}")

    # Create channel instances ---------------------------------------------------------

    @property
    def channel1(self):
        return self.Channel(instrument=self, num=1)

    @property
    def channel2(self):
        return self.Channel(instrument=self, num=2)

    @property
    def channel3(self):
        return self.Channel(instrument=self, num=3)

    @property
    def channel4(self):
        return self.Channel(instrument=self, num=4)

    class Channel:
        def __init__(self, instrument, num):
            self.instrument = instrument
            self.num = num

        def read(self):
            return self.instrument.read()

        def write(self, command):
            self.instrument.write(f"C{self.num}:{command}")

        def ask(self, command):
            return self.instrument.ask(f"C{self.num}:{command}")

        def values(self, command, **kwargs):
            """
            Reads a set of values from the instrument through the adapter, passing on
            any keyword arguments.
            """
            return self.instrument.values(f"C{self.num}:{command}", **kwargs)

        coupling = Instrument.control(
            "COUPLING?",
            "COUPLING %s",
            "The coupling of the channel, e.g. D50 for 50Ω DC-coupling"
            "A - alternating current"
            "D - direct current"
            "1M - 1 MΩ input impedance"
            "50 - 50Ω input impedance"
            "GND - ground",
            validator=strict_discrete_set,
            values=["A1M", "D1M", "A50", "D50", "GND"],
        )

        offset = Instrument.control(
            "OFST?", "OFST %s", "The offset of the channel in volts."
        )

        trace = Instrument.control(
            "TRACE?",
            "TRACE %s",
            "Turn the display of the channel on or off",
            values={True: "ON", False: "OFF"},
            map_values=True,
        )

        volt_div = Instrument.control(
            "VDIV?", "VDIV %s", "Vertical sensitivity in volts/div"
        )

        def get_waveform(self):
            self.write("WF? DAT2")
            # FIXME: there should be a more elegant way of doing this
            recv = self.instrument.adapter.connection.read_raw()
            y = list(recv)[15:-2]
            y = np.array([d - 255 if d > 127 else d for d in y])
            y = y / 25 * self.volt_div - self.offset
            x = (
                -self.instrument.time_div * 14 / 2
                + np.arange(len(y)) * 1 / self.instrument.sample_rate
            )
            return x, y
