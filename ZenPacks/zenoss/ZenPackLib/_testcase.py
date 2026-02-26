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

import logging

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from transaction._transaction import Transaction

LOG = logging.getLogger("zen.ZenPackLib")


class TestCase(BaseTestCase):
    # As in BaseTestCase, the default behavior is to disable
    # all logging from within a unit test.  To enable it,
    # set disableLogging = False in your subclass.  This is
    # recommended during active development, but is too noisy
    # to leave as the default.
    disableLogging = True

    def afterSetUp(self):
        super(TestCase, self).afterSetUp()

        # Not included with BaseTestCase. Needed to test that UI
        # components have been properly registered.
        from Zope2.App import zcml
        import Products.ZenUI3

        zcml.load_config("configure.zcml", Products.ZenUI3)

        if (
            not hasattr(self, "zenpack_module_name")
            or self.zenpack_module_name is None
        ):
            self.zenpack_module_name = ".".join(
                self.__module__.split(".")[:-2]
            )

        try:
            import importlib

            zenpack_module = importlib.import_module(self.zenpack_module_name)
        except Exception:
            LOG.exception(
                "Unable to load zenpack named '%s' - is it installed? (%s)",
                self.zenpack_module_name,
            )
            raise

        zenpackspec = getattr(zenpack_module, "CFG", None)
        if not zenpackspec:
            raise NameError(
                "name {!r} is not defined".format(
                    ".".join((self.zenpack_module_name, "CFG"))
                )
            )

        zenpackspec.test_setup()

        import Products.ZenEvents

        zcml.load_config("meta.zcml", Products.ZenEvents)

        try:
            import ZenPacks.zenoss.DynamicView

            zcml.load_config("configure.zcml", ZenPacks.zenoss.DynamicView)
        except ImportError:
            pass

        try:
            import Products.Jobber

            zcml.load_config("meta.zcml", Products.Jobber)
        except ImportError:
            pass

        try:
            import ZenPacks.zenoss.Impact

            zcml.load_config("meta.zcml", ZenPacks.zenoss.Impact)
            zcml.load_config("configure.zcml", ZenPacks.zenoss.Impact)
        except ImportError:
            pass

        try:
            zcml.load_config("configure.zcml", zenpack_module)
        except IOError:
            pass

        # BaseTestCast.afterSetUp already hides transaction.commit.
        # So we also need to hide transaction.abort.
        self._transaction_abort = Transaction.abort
        Transaction.abort = lambda *x: None

    def beforeTearDown(self):
        super(TestCase, self).beforeTearDown()

        if hasattr(self, "_transaction_abort"):
            Transaction.abort = self._transaction_abort

    # If the exception occurs during setUp, beforeTearDown is not called,
    # so we also need to restore abort here as well:
    def _close(self):
        if hasattr(self, "_transaction_abort"):
            Transaction.abort = self._transaction_abort

        super(TestCase, self)._close()
