#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb import IllegalIdentifierException

from gdrive import Initialization
from gdrive import PropertySet
from gdrive import checkIdentifiers
from gdrive import getConnectionMode
from gdrive import getProperty
from gdrive import getSession
from gdrive import getUser
from gdrive import mergeJsonUser
from gdrive import selectUser

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentUser'


class ContentUser(unohelper.Base, XServiceInfo, Initialization, PropertySet):
    def __init__(self, ctx, *namedvalues):
        self.ctx = ctx
        self.Scheme = None
        self.Connection = None
        self.Name = None
        self.initialize(namedvalues)
        self._Mode = getConnectionMode(self.ctx)
        self.Error = None
        self.Session = None if self.Name is None else getSession(self.ctx, self.Scheme, self.Name)
        user = self._getUser()
        self.user = {} if user is None else user
        if self.IsValid and self.Mode == ONLINE:
            checkIdentifiers(self.Connection, self.Session, self.Id)

    @property
    def Id(self):
        return self.user.get('Id', None)
    @property
    def RootId(self):
        return self.user.get('RootId', None)
    @property
    def IsValid(self):
        return all((self.Id, self.Name, self.RootId, self.Error is None))
    @property
    def Mode(self):
        return self._Mode
    @Mode.setter
    def Mode(self, mode):
        if mode == ONLINE and mode != getConnectionMode(self.ctx):
            return
        self._Mode = mode

    def _getUser(self):
        if self.Name is None:
            message = "ERROR: Can't retrieve a UserName from Handler"
            self.Error = IllegalIdentifierException(message, self)
            return None
        user = selectUser(self.Connection, self.Name, self.Mode)
        if user is None:
            if self.Mode == ONLINE:
                user = self._getUserFromProvider()
            else:
                message = "ERROR: Can't retrieve User: %s Network is Offline" % self.Name
                self.Error = IllegalIdentifierException(message, self)
        return user

    def _getUserFromProvider(self):
        with self.Session as session:
            data, root = getUser(session)
        print("ContentUser._getUserFromProvider(): %s" % self.Name)
        if root is not None:
            user = mergeJsonUser(self.Connection, data, root, self.Mode)
        else:
            message = "ERROR: Can't retrieve User: %s from provider" % self.Name
            user = {'Error': IllegalIdentifierException(message, self)}
        return user

    def _getPropertySetInfo(self):
        properties = {}
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['Connection'] = getProperty('Connection', 'com.sun.star.sdbc.XConnection', maybevoid | readonly)
        properties['Mode'] = getProperty('Mode', 'short', bound | readonly)
        properties['Id'] = getProperty('Id', 'string', maybevoid | bound | readonly)
        properties['Name'] = getProperty('Name', 'string', maybevoid | bound | readonly)
        properties['RootId'] = getProperty('RootId', 'string', maybevoid | bound | readonly)
        properties['IsValid'] = getProperty('IsValid', 'boolean', bound | readonly)
        properties['Error'] = getProperty('Error', 'com.sun.star.ucb.IllegalIdentifierException', maybevoid | bound | readonly)    
        return properties

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