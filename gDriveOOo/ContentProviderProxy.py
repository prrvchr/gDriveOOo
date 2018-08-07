#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.uno import XInterface
from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContentProvider, XContentProviderSupplier, XParameterizedContentProvider

from gdrive import createService

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProviderProxy'


class ContentProviderProxy(unohelper.Base, XServiceInfo, XContentProvider,
                           XContentProviderSupplier, XParameterizedContentProvider):
    def __init__(self, ctx):
        self.ctx = ctx
        self.provider = None
        print("ContentProviderProxy.__init__()")

    # XInterface
    def queryInterface(self, atype):
        print("ContentProviderProxy.queryInterface()")
    def acquire(self):
        print("ContentProviderProxy.acquire()")
    def release(self):
        print("ContentProviderProxy.release()")

    # XContentProviderSupplier
    def getContentProvider(self):
        print("ContentProviderProxy.getContentProvider()")
        if self.provider is None:
            name = "com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider"
            self.provider = createService(name, self.ctx)
        return self.provider

    # XParameterizedContentProvider
    def registerInstance(self, template, argument, replace):
        print("ContentProviderProxy.registerInstance()")
        return self.getContentProvider()
    def deregisterInstance(self, template, argument):
        print("ContentProviderProxy.deregisterInstance()")

    # XContentProvider
    def queryContent(self, identifier):
        print("ContentProviderProxy.queryContent()")
        return self.getContentProvider().queryContent(identifier)
    def compareContentIds(self, identifier1, identifier2):
        print("ContentProviderProxy.compareContentIds()")
        return self.getContentProvider().compareContentIds(identifier1, identifier2)

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(ContentProviderProxy,                                               # UNO object class
                                         g_ImplementationName,                                               # Implementation name
                                        (g_ImplementationName, 'com.sun.star.ucb.ContentProviderProxy'))     # List of implemented services
