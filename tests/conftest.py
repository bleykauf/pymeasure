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

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--instrument-present",
        action="store_true",
        default=False,
        help="""Run tests that need an instrument.
                Provide the resource name via --resource-name."""
    )
    parser.addoption(
        "--resource-name",
        action="store",
        default=None,
        dest="resource_name",
        help="""Pass a resource name for an instrument needed for a test.
                See also --instrument-present."""
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", """needs_instrument:
                        mark test that needs an instrument to be present."""
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--instrument-present"):
        skipper = pytest.mark.skip(
            reason="Only run when --instrument-present is given"
            )
        for item in items:
            if "needs_instrument" in item.keywords:
                item.add_marker(skipper)
