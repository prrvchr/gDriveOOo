#!
# -*- coding: utf_8 -*-

import unohelper

from com.sun.star.lang import XServiceInfo

from gdrive import getUser
from gdrive import mergeJsonUser
from gdrive import selectUser
from gdrive import g_host
from gdrive import g_plugin
from gdrive import checkIdentifiers

# clouducp is only available after CloudUcpOOo as been loaded...
try:
    from clouducp import ContentUserBase
except ImportError:
    class ContentUserBase():
        pass

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = '%s.ContentUser' % g_plugin


class ContentUser(ContentUserBase,
                  XServiceInfo):
    def __init__(self, ctx, *namedvalues):
        ContentUserBase.__init__(self, ctx, namedvalues)

    def getHost(self):
        return g_host
    def selectUser(self):
        return selectUser(self.Connection, self.Name)
    def getUser(self, session):
        return getUser(session)
    def checkIdentifiers(self, session):
        checkIdentifiers(self.Connection, session, self.Id)
    def mergeJsonUser(self, data, root):
        return mergeJsonUser(self.Connection, data, root)

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(ContentUser,                                                        # UNO object class
                                         g_ImplementationName,                                               # Implementation name
                                        (g_ImplementationName, ))                                            # List of implemented services
