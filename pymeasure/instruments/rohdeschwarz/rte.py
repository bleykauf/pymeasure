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

from pymeasure.instruments.instrument import Instrument
from pymeasure.instruments.validators import strict_discrete_set, truncated_range

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class RTE(Instrument):
    def __init__(self, adapter, **kwargs):
        kwargs.setdefault("name", "Rohde&Schwarz RTE")
        super().__init__(adapter, includeSCPI=True, **kwargs)

    data_format = Instrument.control(
        "FORMat:DATA?",
        "FORMat:DATA %s",
        "Data type that is used for transmission of data",
        validator=strict_discrete_set,
        values=["ASCII", "REAL,32", "INT,8", "INT,16"],
    )

    time_scale = Instrument.control(
        "TIMebase:SCALe?",
        "TIMebase:SCALe %s",
        "The time per division on the x-axis",
    )

    time_div = Instrument.measurement(
        "TIMebase:DIVisions?", "Number of horizontal divisions on the screen"
    )

    time_ref = Instrument.control(
        "TIMebase:REFerence?",
        "TIMebase:REFerence %s",
        "Position of the reference point in % of the screen",
        validator=truncated_range,
        values=[1, 100],
    )

    # Create channel instances ---------------------------------------------------------------------

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
            self.instrument.write(f"CHANnel{self.num}:{command}")

        def ask(self, command):
            return self.instrument.ask(f"CHANnel{self.num}:{command}")

        def values(self, command, **kwargs):
            """
            Read a set of values from the instrument through the adapter, passing on any keyword
            arguments.
            """
            return self.instrument.values(f"CHANnel{self.num}:{command}", **kwargs)

        def get_waveform(self, offset=None, length=None):
            """
            Return the data of the channel waveform points.

            :param offset: Number of offset waveform points. Defaults to None
            :type offset: int, optional
            :param length: Number of waveform points to be retrieved. Defaults to None
            :type length: int, optional
            """
            if self.instrument.data_format[0] != "ASC":
                raise NotImplementedError(
                    "Currently, only ASCII format is supported. "
                    "Set it via the `data_format` attribute."
                )
            query = "DATA?"
            if offset:
                query += f" {offset}"
            if length:
                query += f" {length}"
            return self.values(query)
