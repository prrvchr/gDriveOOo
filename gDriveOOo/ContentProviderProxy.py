#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo, XEventListener
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory, XContentProviderSupplier, XParameterizedContentProvider

from gdrive import createService

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProviderProxy'


class ContentProviderProxy(unohelper.Base, XServiceInfo, XContentProvider, XContentIdentifierFactory,
                           XEventListener, XContentProviderSupplier, XParameterizedContentProvider):
    def __init__(self, ctx):
        self.ctx = ctx
        self.provider = None
        self.template = ''
        self.arguments = ''
        self.replace = True
        print("ContentProviderProxy.__init__()")

    # XEventListener
    def disposing(self, source):
        print("ContentProviderProxy.disposing()")

    # XContentProviderSupplier
    def getContentProvider(self):
        print("ContentProviderProxy.getContentProvider()")
        if self.provider is None:
            self.provider = createService('com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider', self.ctx)
            #provider = factory.createContentProvider("com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider")
            self.provider.registerInstance(self.template, self.arguments, self.replace)
            self.provider.addEventListener(self)
        return self.provider

    # XParameterizedContentProvider
    def registerInstance(self, template, arguments, replace):
        print("ContentProviderProxy.registerInstance(): %s - %s - %s" % (template, arguments, replace))
        self.template = template
        self.arguments = arguments
        self.replace = replace
        return self
    def deregisterInstance(self, template, argument):
        print("ContentProviderProxy.deregisterInstance()")

    # XContentIdentifierFactory
    def createContentIdentifier(self, identifier):
        return self.getContentProvider().createContentIdentifier(identifier)

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
