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
from math import log10, sqrt

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_discrete_set, strict_range


class Channel:
    def __init__(self, instrument, number):
        self.instrument = instrument
        self.number = number

    def ask(self, command):
        return self.instrument.ask(f"source{self.number}:{command}")

    def read(self):
        return self.instrument.read()

    def write(self, command):
        self.instrument.write(f"source{self.number}:{command}")

    def values(self, command, **kwargs):
        """
        Reads a set of values from the instrument through the adapter,
        passing on any key-word arguments.
        """
        return self.instrument.values(f"source{self.number}:{command}", **kwargs)

    def enable(self):
        self.instrument.write(f"output{self.number}:state on")

    def disable(self):
        self.instrument.write(f"output{self.number}:state off")

    shape = Instrument.control(
        "function:shape?",
        "function:shape %s",
        """ A string property that controls the shape of the output.
            This property can be set.""",
        validator=strict_discrete_set,
        values={
            "sinusoidal": "SIN",
            "square": "SQU",
            "pulse": "PULS",
            "ramp": "RAMP",
            "prnoise": "PRN",
            "dc": "DC",
            "sinc": "SINC",
            "gaussian": "GAUS",
            "lorentz": "LOR",
            "erise": "ERIS",
            "edecay": "EDEC",
            "haversine": "HAV",
            "user1": "USER1",
            "user2": "USER2",
            "user3": "USER3",
            "user4": "USER4",
        },
        map_values=True,
    )

    unit = Instrument.control(
        "voltage:unit?",
        "voltage:unit %s",
        """ A string property that controls the amplitude unit.
            This property can be set.""",
        validator=strict_discrete_set,
        values=["VPP", "VRMS", "DBM"],
    )

    amp_vpp = Instrument.control(
        "voltage:amplitude?",
        "voltage:amplitude %eVPP",
        """ A floating point property that controls the output amplitude
            in Vpp. This property can be set.""",
        validator=strict_range,
        values=[20e-3, 10],
    )

    amp_dbm = Instrument.control(
        "voltage:amplitude?",
        "voltage:amplitude %eDBM",
        """ A floating point property that controls the output amplitude
            in dBm. This property can be set.""",
        validator=strict_range,
        values=list(map(lambda x: round(20 * log10(x / 2 / sqrt(0.1)), 2), [20e-3, 10])),
    )

    amp_vrms = Instrument.control(
        "voltage:amplitude?",
        "voltage:amplitude %eVRMS",
        """ A floating point property that controls the output amplitude
            in Vrms. This property can be set.""",
        validator=strict_range,
        values=list(map(lambda x: round(x / 2 / sqrt(2), 3), [20e-3, 10])),
    )

    offset = Instrument.control(
        "voltage:offset?",
        "voltage:offset %e",
        """ A floating point property that controls the amplitude
            offset. It is always in Volt. This property can be set.""",
    )

    frequency = Instrument.control(
        "frequency:fixed?",
        "frequency:fixed %e",
        """ A floating point property that controls the frequency.
            This property can be set.""",
        validator=strict_range,
        values=[1e-6, 150e6],  # frequeny limit for sinusoidal function
    )

    duty = Instrument.control(
        "pulse:dcycle?",
        "pulse:dcycle %.3f",
        """ A floating point property that controls the duty
            cycle of pulse. This property can be set.""",
        validator=strict_range,
        values=[0.001, 99.999],
    )

    impedance = Instrument.control(
        "output:impedance?",
        "output:impedance %d",
        """ A floating point property that controls the output
            impedance of the channel. Be careful with this.
            This property can be set.""",
        validator=strict_range,
        values=[1, 1e4],
        cast=int,
    )

    def waveform(self, shape="SIN", frequency=1e6, units="VPP", amplitude=1, offset=0):
        """General setting method for a complete wavefunction"""
        self.write(f"function:shape {shape}")
        self.write(f"frequency:fixed {frequency:.6E}")
        self.write(f"voltage:unit {units}%s")
        self.write(f"voltage:amplitude {amplitude:.6E}{units}")
        self.instrument.write("voltage:offset {offset:.6E}V")


class AFG3152C(Instrument):
    """Represents the Tektronix AFG 3000 series (one or two channels)
    arbitrary function generator and provides a high-level for
    interacting with the instrument.

        afg=AFG3152C("GPIB::1")        # AFG on GPIB 1
        afg.reset()                    # Reset to default
        afg.ch1.shape='sinusoidal'     # Sinusoidal shape
        afg.ch1.unit='VPP'             # Sets CH1 unit to VPP
        afg.ch1.amp_vpp=1              # Sets the CH1 level to 1 VPP
        afg.ch1.frequency=1e3          # Sets the CH1 frequency to 1KHz
        afg.ch1.enable()               # Enables the output from CH1
    """

    def __init__(self, adapter, **kwargs):
        super().__init__(
            adapter, "Tektronix AFG3152C arbitrary function generator", includeSCPI=True, **kwargs
        )
        self.ch1 = Channel(self, 1)
        self.ch2 = Channel(self, 2)

    def beep(self):
        self.write("system:beep")
