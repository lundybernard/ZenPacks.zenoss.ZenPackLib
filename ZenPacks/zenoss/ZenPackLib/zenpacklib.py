#!/usr/bin/env python

##############################################################################
# This program is part of zenpacklib, the ZenPack API.
# Copyright (C) 2013-2016  Zenoss, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
##############################################################################

"""zenpacklib - ZenPack API.

This module provides a single integration point for common ZenPacks.

"""

from __future__ import absolute_import, print_function

import logging

# these are the base classes for zenpacklib.Device, zenpacklib.Component,
# zenpacklib.HardwareComponent
from .lib.base.Component import (
    Component,
    CPU,
    ExpansionCard,
    Fan,
    FileSystem,
    HardDisk,
    HardwareComponent,
    HWComponent,
    IpInterface,
    IpRouteEntry,
    IpService,
    OSComponent,
    OSProcess,
    PowerSupply,
    Service,
    TemperatureSensor,
    WinService,
)
from .lib.base.Device import Device
from .lib.functions import (
    catalog_search,
    relationships_from_yuml,
    relname_from_classname,
    ucfirst,
)
from .lib.helpers.utils import load_yaml

# PEP-396 version. (https://www.python.org/dev/peps/pep-0396/)
__version__ = "2.2.0"

# Must defer definition of TestCase. Otherwise it imports
# BaseTestCase which puts Zope into testing mode.
TestCase = None

LOG = logging.getLogger("zen.ZenPackLib")


def enableTesting():
    """Enable test mode. Only call from code under tests/.

    If this is called from production code it will cause all Zope
    clients to start in test mode. Which isn't useful for anything but
    unit testing.

    """
    global TestCase

    if TestCase:
        return

    from . import _testcase

    TestCase = _testcase.TestCase


__all__ = (
    "catalog_search",
    "Component",
    "CPU",
    "Device",
    "enableTesting",
    "ExpansionCard",
    "Fan",
    "FileSystem",
    "HardDisk",
    "HardwareComponent",
    "HWComponent",
    "IpInterface",
    "IpRouteEntry",
    "IpService",
    "load_yaml",
    "OSComponent",
    "OSProcess",
    "PowerSupply",
    "relationships_from_yuml",
    "relname_from_classname",
    "Service",
    "TemperatureSensor",
    "ucfirst",
    "WinService",
)


if __name__ == "__main__":
    from .lib.libexec.ZPLCommand import ZPLCommand

    script = ZPLCommand()
    script.run()
