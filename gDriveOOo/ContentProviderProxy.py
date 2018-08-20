#!
# -*- coding: utf_8 -*-

import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory
from com.sun.star.ucb import XContentProviderSupplier, XParameterizedContentProvider

from gdrive import createService, getUcp

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProviderProxy'


class ContentProviderProxy(unohelper.Base, XServiceInfo, XContentProvider, XContentIdentifierFactory,
                           XContentProviderSupplier, XParameterizedContentProvider):
    def __init__(self, ctx):
        self.ctx = ctx
        self.registered = False
        self.template = ''
        self.arguments = ''
        self.replace = True

    # XContentProviderSupplier
    def getContentProvider(self):
        if not self.registered:
            provider = createService('com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider', self.ctx)
            provider.registerInstance(self.template, self.arguments, self.replace)
            self.registered = True
        else:
            provider = getUcp(self.ctx, self.template)
        return provider

    # XParameterizedContentProvider
    def registerInstance(self, template, arguments, replace):
        self.template = template
        self.arguments = arguments
        self.replace = replace
        return self
    def deregisterInstance(self, template, argument):
        self.getContentProvider().deregisterInstance(template, argument)

    # XContentIdentifierFactory
    def createContentIdentifier(self, identifier):
        return self.getContentProvider().createContentIdentifier(identifier)

    # XContentProvider
    def queryContent(self, identifier):
        return self.getContentProvider().queryContent(identifier)
    def compareContentIds(self, identifier1, identifier2):
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
