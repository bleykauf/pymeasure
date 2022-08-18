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

import numpy as np
from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import (strict_discrete_set,
                                              strict_range,
                                              truncated_discrete_set)


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
        Read a set of values from the instrument through the adapter, passing on any keyword
        arguments.
        """
        return self.instrument.values(f"source{self.number}:{command}", **kwargs)

    def enable(self):
        self.instrument.write(f"output{self.number}:state on")

    def disable(self):
        self.instrument.write(f"output{self.number}:state off")

    shape = Instrument.control(
        "function:shape?",
        "function:shape %s",
        "A string property that controls the shape of the output. This property can be set.",
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
            "emem": "EMEM",
        },
        map_values=True,
    )

    unit = Instrument.control(
        "voltage:unit?",
        "voltage:unit %s",
        "A string property that controls the amplitude unit. This property can be set.",
        validator=strict_discrete_set,
        values=["VPP", "VRMS", "DBM"],
    )

    @property
    def amplitude(self):
        """"
        The amplitude of the waveform.
        
        Unit depends on the current value of the `unit` attribute. This attribute can either be set
        by a numerical value (unit then depends on the value of the `unit` attribute`) or by a tuple
        of a numerical value and an unit ("VPP", "VRMS" or "DBM"), e.g. (3, 'VPP').
        """
        return self.values("VOLT:AMPL?")[0]

    @amplitude.setter
    def amplitude(self, amplitude):
        if isinstance(amplitude, (tuple, list)):
            value, unit = amplitude
        else:
            value = amplitude
            unit = self.unit
        unit = strict_discrete_set(unit, ["VPP", "VRMS", "DBM"])
        if unit == "VPP":
            value = truncated_discrete_set(value, np.arange(20e-3, 10.0001, step=0.1e-3))
        elif unit == "VRMS":
            value = truncated_discrete_set(value, np.arange(7.1e-3, 3.5361, step=0.1e-3))
        elif unit == "DBM":
            value = truncated_discrete_set(value, np.arange(-30, 23.9801, step=0.1e-3))
        self.write(f"FREQ:AMPL {value}{unit}")

    offset = Instrument.control(
        "voltage:offset?",
        "voltage:offset %e",
        """Floating point property that controls the amplitude  offset. It is always in volts. This
           property can be set.""",
    )

    @property
    def frequency(self):
        "Floating point property that controls the frequency. This property can be set."
        return self.values("FREQ:FIX?")[0]

    @frequency.setter
    def frequency(self, value):
        value = strict_range(value, self.instrument._validator_values["frequency"])
        self.write(f"FREQ:FIX {value:.6E}")

    duty = Instrument.control(
        "pulse:dcycle?",
        "pulse:dcycle %.3f",
        """Floating point property that controls the duty cycle ofa  pulse. This property can be
           set.""",
        validator=strict_range,
        values=[0.001, 99.999],
    )

    impedance = Instrument.control(
        "output:impedance?",
        "output:impedance %d",
        """Floating point property that controls the output impedance of the channel. Be careful
           with this. This property can be set.""",
        validator=strict_range,
        values=[1, 1e4],
        cast=int,
    )

    def waveform(self, shape="sinusoidal", frequency=1e6, amplitude=None, unit=None, offset=0):
        """
        Set all parameters necessary for loading a waveform to the channel.

        :param shape: one of the default shapes (e.g. 'gaussian'), a user memory slot (e.g.
            'user2') or edit memory ('emem')
        :type shape: str
        :param frequency: frequency of the waveform in hertz, default 1 MHz
        :type frequency: float
        :param amplitude: amplitude of the waveform in units of `unit`
        :param units: unit for the amplitude, 'VPP' , 'VRMS' or 'DBM'; if not unit is provided, the
            current value of the `unit` attribute is used.
        :type unit: str
        :param offset: Offset of the waveform in volts
        :type offset: float
        """
        self.shape = shape
        self.frequency = frequency
        if unit:
            amplitude = (amplitude, unit)
        if amplitude:
            self.amplitude = amplitude
        self.offset = offset


class EditMemory:
    """Represents the edit memory of the instrument."""

    def __init__(self, instrument):
        self.instrument = instrument

    def ask(self, command):
        return self.instrument.ask(command)

    def read(self):
        return self.instrument.read()

    def write(self, command):
        self.instrument.write(command)

    def values(self, command, **kwargs):
        """
        Read a set of values from the instrument through the adapter, passing on any keyword
        arguments.
        """
        return self.instrument.values(command, **kwargs)

    waveform_length = Instrument.control(
        "DATA:POIN? EMEM",
        "DATA:POIN EMEM, %d",
        "Set or query the number of data points for the waveform created in the edit memory.",
        validator=strict_discrete_set,
        values=[*"MIN", "MAX", *list(range(2, 131073))],
    )

    min_waveform_length = Instrument.measurement(
        "DATA:POIN? EMEM, MIN",
        "Minimum number of data points for a waveform created in the edit memory.",
    )

    max_waveform_length = Instrument.measurement(
        "DATA:POIN? EMEM, MAX",
        "Maximum number of data points for a waveform created in the edit memory.",
    )

    def load_waveform(self, source):
        """
        Load the contents of a user waveform memory to edit memory.

        :param source: the source memory to copy from, "USER1", "USER2", "USER3", "USER4"
        """
        source = strict_discrete_set(source, ["USER1", "USER2", "USER3", "USER4"])
        self.write(f"DATA:COPY EMEM,{source}")

    @property
    def waveform(self):
        """Set or get the waveform in the edit memory."""
        return self.instrument.adapter.connection.query_binary_values(
            "DATA:DATA? EMEM", datatype="H", is_big_endian=True, container=list
        )

    @waveform.setter
    def waveform(self, waveform):
        if (len(waveform) < 2) or (len(waveform) > 131073):
            raise ValueError("Length of the waveform must be between 2 and 131073.")
        self.instrument.adapter.connection.write_binary_values(
            "DATA:DATA EMEM,", waveform, datatype="H", is_big_endian=True
        )

    def save_waveform(self, destination):
        """
        Copy the contents of edit memory to a specified user waveform memory.

        :param destination: the destination memory to copy to, "USER1", "USER2", "USER3", "USER4"
        """
        self.destination = strict_discrete_set(destination, ["USER1", "USER2", "USER3", "USER4"])
        self.write(f"DATA:COPY {destination},EMEM")

    @staticmethod
    def normalize_waveform(waveform):
        """
        Normalize a waveform to span the vertical resolution of the AFG.

        :param waveform: unnormalized waveform
        :type sequence: list-like of numeric
        :return: normalized waveform.
        :rtype: ndarray of int
        """

        resolution = 16383  # 14 bit
        waveform = waveform - min(waveform)
        norm_waveform = waveform / max(waveform) * resolution
        return norm_waveform.astype(np.int)


class AFG3100Series(Instrument):
    """
    Represents an arbitrary function generator from the Tektronix AFG3000(C) series.
    """

    def __init__(self, adapter, name, **kwargs):
        super().__init__(adapter, name=name, includeSCPI=True, **kwargs)
        self.ch1 = Channel(self, 1)
        self.ch2 = Channel(self, 2)
        self.edit_memory = EditMemory(self)

    def beep(self):
        self.write("system:beep")

    def generate_trigger(self):
        """Generate a trigger event."""
        self.write("*TRG")

    waveform_catalog = Instrument.measurement(
        "DATA:CAT?", "Names of user waveform memory and edit memory"
    )


class AFG3102(AFG3100Series):
    __doc__ = AFG3100Series.__doc__

    def __init__(self, adapter, **kwargs):
        super().__init__(adapter, "Tektronix AFG3102", **kwargs)
        self._validator_values = {
            "frequency": [1e-6, 100e6],
        }


class AFG3152C(AFG3100Series):
    __doc__ = AFG3100Series.__doc__

    def __init__(self, adapter, **kwargs):
        super().__init__(adapter, "Tektronix AFG3152C", **kwargs)
        self._validator_values = {
            "frequency": [1e-6, 150e6],
        }
