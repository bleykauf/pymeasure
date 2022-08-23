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

from abc import ABC

import numpy as np
from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import (
    strict_discrete_set,
    strict_range,
    truncated_discrete_set,
)


class Channel:
    def __init__(self, instrument, number):
        self.instrument = instrument
        self.number = number
        self.burst_mode = BurstMode(self.instrument, self.number)
        self.pulse_mode = PulseMode(self.instrument, self.number)
        self.sweep_mode = SweepMode(self.instrumet, self.number)

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
        "Shape of the output, either a build-in shape, a user memory slot or the edit memory.",
        validator=strict_discrete_set,
        set_process=lambda s: f"USER{s}" if isinstance(s, int) else s,
        values=[
            "SIN",
            "SQU",
            "PULS",
            "RAMP",
            "PRN",
            "DC",
            "SINC",
            "GAUS",
            "LOR",
            "ERIS",
            "EDEC",
            "HAV",
            "USER1",
            "USER2",
            "USER3",
            "USER4",
            1,
            2,
            3,
            4,
            "EMEM",
        ],
    )

    unit = Instrument.control(
        "voltage:unit?",
        "voltage:unit %s",
        "Amplitude unit",
        validator=strict_discrete_set,
        values=["VPP", "VRMS", "DBM"],
    )

    @property
    def amplitude(self):
        """
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
            value = truncated_discrete_set(
                value, np.arange(20e-3, 10.0001, step=0.1e-3)
            )
        elif unit == "VRMS":
            value = truncated_discrete_set(
                value, np.arange(7.1e-3, 3.5361, step=0.1e-3)
            )
        elif unit == "DBM":
            value = truncated_discrete_set(value, np.arange(-30, 23.9801, step=0.1e-3))
        self.write(f"VOLT:AMPL {value}{unit}")

    offset = Instrument.control(
        "voltage:offset?",
        "voltage:offset %e",
        "Amplitude  offset in volts",
    )

    @property
    def frequency(self):
        "Frequency of the waveform."
        return self.values("FREQ:FIX?")[0]

    @frequency.setter
    def frequency(self, value):
        value = strict_range(value, self.instrument._validator_values["frequency"])
        self.write(f"FREQ:FIX {value:.6E}")

    impedance = Instrument.control(
        "output:impedance?",
        "output:impedance %d",
        "Output impedance of the channel.",
        validator=strict_discrete_set,
        values=range(1, 10001),
        cast=int,
    )

    def waveform(self, shape="SIN", frequency=1e6, amplitude=None, unit=None, offset=0):
        """
        Set all parameters necessary for loading a waveform to the channel.

        :param shape: one of the default shapes (e.g. 'GAUS'), a user memory slot (e.g. 'USER') or
            edit memory ('EMEM')
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


class Mode(ABC):
    """Represents a mode of the channel. Must be subclassed by a specific mode."""

    def __init__(self, instrument, channel_number):
        self.instrument = instrument
        self.channel_number = channel_number

    def ask(self, command):
        return self.instrument.ask(f"SOUR{self.channel_number}:{command}")

    def read(self):
        return self.instrument.read()

    def write(self, command):
        self.instrument.write(f"SOUR{self.channel_number}:{command}")

    def values(self, command, **kwargs):
        """
        Read a set of values from the instrument through the adapter, passing on any keyword
        arguments.
        """
        return self.instrument.values(
            f"source{self.channel_number}:{command}", **kwargs
        )


class BurstMode(Mode):
    """Represents the burst mode."""

    enabled = Instrument.control(
        "SWEE:STAT?",
        "SWEE:STAT %s",
        "Enable (True) or disable (False) burst mode.",
        validator=strict_discrete_set,
        values={False: 0, True: 1},
        map_values=True,
    )

    mode = Instrument.control(
        "SWEE:MODE?",
        "SWEE:MODE %s",
        "Burst mode can be either TRIGerred or GATed.",
        validator=strict_discrete_set,
        values=["TRIG", "GAT"],
    )

    n_cycles = Instrument.control(
        "NCYC?",
        "NCYC %s",
        "Number of cycles (burst count) to be output in burst mode.",
        validator=strict_discrete_set,
        # FIXME: returns 9.9E37 for infinity, should be mapped to "INF"
        values=["INF", "MIN", "MAX", *list(range(1, int(1e6)))],
        cast=int,
    )


class PulseMode(Mode):
    """Represents the pulse mode."""

    duty_cycle = Instrument.control(
        "PULS:DCYC?",
        "PULS:DCYC %.3f",
        "Duty cycle of a  pulse. ",
        validator=strict_range,
        values=[0.001, 99.999],
    )


class SweepMode(Mode):
    """Represents the sweep mode."""

    mode = Instrument.control(
        "SWE:MODE?",
        "SWE:MODE %s",
        """
        Sweep mode can be either AUTO or MANual.
        In AUTO mode, the instrument outputs a continuous sweep at the rate specified by
        `sweep_time`, `hold_time` and `return_time`.
        In MANual mode, the instrument outputs one sweep when the trigger input is received.
        """,
        validator=strict_discrete_set,
        values=["AUTO", "MAN"],
    )

    frequency_center = Instrument.control(
        "FREQ:CENT?",
        "FREQ:CENT %s",
        """
        Center frequency of the sweep in hertz or "MIN", "MAX". Range depends on the selected
        waveform, see Quick Start User Manual.
        """,
    )

    frequency_span = Instrument.control(
        "FREQ:SPAN?",
        "FREQ:SPAN} %s",
        """
        Frequency span of the sweep in hertz or "MIN", "MAX". Range depends on the selected
        waveform, see Quick Start User Manual.
        """,
    )

    frequency_start = Instrument.control(
        "FREQ:STAR?",
        "FREQ:STAR %s",
        """
        Start frequency of the sweep in hertz or "MIN", "MAX". Range depends on the selected
        waveform, see Quick Start User Manual.
        """,
    )

    frequency_stop = Instrument.control(
        "FREQ:STOP?",
        "FREQ:STOP %s",
        """
        Stop frequency of the sweep in hertz or "MIN", "MAX". Range depends on the selected
        waveform, see Quick Start User Manual.
        """,
    )

    min_hold_time = Instrument.measurement(
        "SWE:HTIM? MIN", "Minimum hold time in seconds."
    )

    max_hold_time = Instrument.measurement(
        "SWE:HTIM? MAX?", "Maximum hold time in seconds."
    )

    hold_time = Instrument.control(
        "SWE:HTIM?",
        "SWE:HTIM %s",
        """
        Sweep hold time in seconds, i.e. the amount of time that the freqeuncy must remain stable
        after reaching the stop frequency. Can be set to "MIN" or "MAX".
        """,
    )

    min_return_time = Instrument.measurement(
        "SWE:RTIM? MIN", "Minimum return time in seconds."
    )

    max_return_time = Instrument.measurement(
        "SWE:RTIM? MAX?", "Maximum return time in seconds."
    )

    return_time = Instrument.control(
        "SWE:RTIM?",
        "SWE:RTIM %s",
        """
        Sweep return time in seconds, i.e. the amount of time from stop frequency through start
        frequency. Does not include hold time.
        """,
    )

    spacing = Instrument.control(
        "SWE:SPAC?",
        "SWE:SPAC %s",
        "Sweep spacing can be either LINear or LOGarithic.",
        validator=strict_discrete_set,
        values=["LIN", "LOG"],
    )

    time = Instrument.control(
        "SWE:TIME?",
        "SWE:TIME %s",
        """
        Sweep time in seconds can range from 1 ms to 300 s or can be set to "MIN", "MAX". Does not
        include hold and return time.
        """,
    )


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

    shape_length = Instrument.control(
        "DATA:POIN? EMEM",
        "DATA:POIN EMEM, %d",
        "Set or query the number of data points for the shape created in the edit memory.",
        validator=strict_discrete_set,
        values=[*"MIN", "MAX", *list(range(2, 131073))],
    )

    min_shape_length = Instrument.measurement(
        "DATA:POIN? EMEM, MIN",
        "Minimum number of data points for a shape created in the edit memory.",
    )

    max_shape_length = Instrument.measurement(
        "DATA:POIN? EMEM, MAX",
        "Maximum number of data points for a shape created in the edit memory.",
    )

    @property
    def shape(self):
        """The waveform in the edit memory."""
        return self.instrument.adapter.connection.query_binary_values(
            "DATA:DATA? EMEM", datatype="H", is_big_endian=True, container=list
        )

    @shape.setter
    def shape(self, shape):
        if (len(shape) < 2) or (len(shape) > 131073):
            raise ValueError("Length of the shape must be between 2 and 131073.")
        self.instrument.adapter.connection.write_binary_values(
            "DATA:DATA EMEM,", shape, datatype="H", is_big_endian=True
        )

    def load_shape(self, source):
        """
        Load the contents of a user memory to edit memory.

        :param source: the source memory to copy from, "USER1", "USER2", "USER3", "USER4" or 1, 2,
            3, 4
        :type source: str or int
        """
        source = strict_discrete_set(
            source, ["USER1", "USER2", "USER3", "USER4", 1, 2, 3, 4]
        )
        self.write(f"DATA:COPY EMEM,{source}")

    def save_shape(self, destination):
        """
        Copy the contents of edit memory to a specified user memory.

        :param destination: the destination memory to copy to, "USER1", "USER2", "USER3", "USER4" or
            1, 2, 3, 4
        :type destination: str or int
        """
        self.destination = strict_discrete_set(
            destination, ["USER1", "USER2", "USER3", "USER4", 1, 2, 3, 4]
        )
        if isinstance(destination, int):
            destination = f"USER{destination}"
        self.write(f"DATA:COPY {destination},EMEM")

    @staticmethod
    def normalize_shape(shape):
        """
        Normalize a waveform to span the vertical resolution of the AFG.

        :param shape: unnormalized shape
        :type sequence: list-like of numeric
        :return: normalized shape.
        :rtype: ndarray of int
        """

        resolution = 16383  # 14 bit
        shape = shape - min(shape)
        norm_shape = shape / max(shape) * resolution
        return norm_shape.astype(np.int)


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

    def force_trigger(self):
        """Force a trigger event to occur."""
        self.write("TRIG")

    trigger_source = Instrument.control(
        "TRIG:SOUR?",
        "TRIG:SOUR %s",
        "Trigger source is TIMer or EXTernal.",
        validator=strict_discrete_set,
        values=["TIM", "EXT"],
    )

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
