##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from zope.component import adapts
from zope.interface import  implementer
from Products.Zuul.decorators import info
from Products.Zuul.infos.component import ComponentInfo
from .base.Component import HWComponent, HardwareComponent
from .interfaces import IHWComponentInfo, IHardwareComponentInfo

@implementer(IHWComponentInfo)
class HWComponentInfo(ComponentInfo):

    """Info adapter factory for ZPL HWComponent.
    This exists because Zuul has no HWComponent info adapter.
    """

    adapts(HWComponent)

    @property
    @info
    def manufacturer(self):
        """Return Info for hardware product class' manufacturer."""
        product_class = self._object.productClass()
        if product_class:
            return product_class.manufacturer()

    @property
    @info
    def product(self):
        """Return Info for hardware product class."""
        return self._object.productClass()

HardwareComponentInfo = HWComponentInfo
