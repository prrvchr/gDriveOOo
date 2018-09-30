#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory
from com.sun.star.ucb import XContentProviderSupplier, XParameterizedContentProvider

from gdrive import PropertySet
from gdrive import createService, getUcp, getProperty

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProviderProxy'


class ContentProviderProxy(unohelper.Base, XServiceInfo, XContentProvider, XContentIdentifierFactory,
                           XContentProviderSupplier, XParameterizedContentProvider, PropertySet):
    def __init__(self, ctx):
        self.ctx = ctx
        self.registred = False
        self.template = ''
        self.arguments = ''
        self.replace = True
        self.UserName = None

    # XContentProviderSupplier
    def getContentProvider(self):
        print("ContentProviderProxy.getContentProvider() 1")
        if not self.registred:
            name = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider'
            print("ContentProviderProxy.getContentProvider() 2")
            provider = createService(name, self.ctx).registerInstance(self.template, self.arguments, self.replace)
            print("ContentProviderProxy.getContentProvider() 3")
            self.registred = True
        else:
            provider = getUcp(self.ctx)
        return provider

    # XParameterizedContentProvider
    def registerInstance(self, template, arguments, replace):
        print("ContentProviderProxy.registerInstance() 1")
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

    # PropertySet
    def _getPropertySetInfo(self):
        properties = {}
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['UserName'] = getProperty('UserName', 'string', maybevoid | readonly)
        return properties

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
