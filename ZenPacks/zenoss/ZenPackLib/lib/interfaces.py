##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from six import u as _u

from Products.Zuul.form import schema
from Products.Zuul.interfaces.component import IComponentInfo


class IHWComponentInfo(IComponentInfo):

    """Info interface for ZPL HWComponent.

    This exists because Zuul has no HWComponent info interface.
    """

    manufacturer = schema.Entity(title=_u('Manufacturer'))
    product = schema.Entity(title=_u('Model'))


IHardwareComponentInfo = IHWComponentInfo
