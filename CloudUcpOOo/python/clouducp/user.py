#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE
from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb import XRestUser


from .dbinit import getDataSourceUrl
from .dbtools import getDataSourceConnection

from .configuration import g_identifier
from .identifier import Identifier
from .logger import logMessage

import traceback


class User(unohelper.Base,
           XRestUser):
    def __init__(self, ctx, datasource, name):
        msg = "User loading"
        self.ctx = ctx
        self._Statement = None
        self._Warnings = None
        self.Request = datasource.getRequest(name)
        self.MetaData = datasource.selectUser(name)
        self._Error = ''

        msg += " ... Done"
        logMessage(self.ctx, INFO, msg, "User", "__init__()")

    @property
    def Id(self):
        return self.MetaData.getDefaultValue('UserId', None)
    @property
    def Name(self):
        return self.MetaData.getDefaultValue('UserName', None)
    @property
    def RootId(self):
        return self.MetaData.getDefaultValue('RootId', None)
    @property
    def RootName(self):
        return self.MetaData.getDefaultValue('RootName', None)
    @property
    def Token(self):
        return self.MetaData.getDefaultValue('Token', '')
    @property
    def IsValid(self):
        return all((self.Id, self.Name, self.RootId, self.RootName, not self.Error, self.Warnings is None))
    @property
    def Error(self):
        return self.Request.Error if self.Request and self.Request.Error else self._Error
    @property
    def Connection(self):
        if self._statement is not None:
            return self._statement.getConnection()
        return None

    @property
    def Warnings(self):
        return self._Warnings
    @Warnings.setter
    def Warnings(self, warning):
        if warning is None:
            return
        warning.NextException = self._Warnings
        self._Warnings = warning

    def getWarnings(self):
        return self._Warnings
    def clearWarnings(self):
        self._Warnings = None

    def _setSessionMode(self, provider):
        provider.SessionMode = self.Request.getSessionMode(provider.Host)

    def initialize(self, datasource, name):
        print("User.initialize() 1")
        init = False
        provider = datasource.Provider
        self.Request.initializeSession(provider.Scheme, name)
        self._setSessionMode(provider)
        user = datasource.selectUser(name)
        if user is not None:
            self.MetaData = user
            init = True
        elif provider.isOnLine():
            user = provider.getUser(self.Request, name)
            if user.IsPresent:
                root = provider.getRoot(self.Request, user.Value)
                if root.IsPresent:
                    self.MetaData = datasource.insertUser(user.Value, root.Value)
                    init = True
        else:
            self._Error = "ERROR: Can't retrieve User: %s from provider network is OffLine" % name
        print("User.initialize() 2 %s" % self.MetaData)
        return init

    def getItem(self, datasource, identifier):
        item = datasource.selectItem(self.MetaData, identifier)
        provider = datasource.Provider
        if not item and provider.isOnLine():
            data = provider.getItem(self.Request, identifier)
            if data.IsPresent:
                item = datasource.insertItem(self.MetaData, data.Value)
        return item

    def insertNewDocument(self, datasource, itemid, parentid, content):
        inserted = datasource.insertNewDocument(self.Id, itemid, parentid, content)
        return self.synchronize(datasource, inserted)
    def insertNewFolder(self, datasource, itemid, parentid, content):
        inserted = datasource.insertNewFolder(self.Id, itemid, parentid, content)
        print("User.insertNewFolder() %s" % inserted)
        return self.synchronize(datasource, inserted)

    # XRestUser

    def updateTitle(self, datasource, itemid, parentid, value, default):
        result = datasource.updateTitle(self.Id, itemid, parentid, value, default)
        return self.synchronize(datasource, result)
    def updateSize(self, datasource, itemid, parentid, size):
        print("User.updateSize() ***********************")
        result = datasource.updateSize(self.Id, itemid, parentid, size)
        return self.synchronize(datasource, result)
    def updateTrashed(self, datasource, itemid, parentid, value, default):
        result = datasource.updateTrashed(self.Id, itemid, parentid, value, default)
        return self.synchronize(datasource, result)

    def getInputStream(self, url):
        sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
        if sf.exists(url):
            return sf.getSize(url), sf.openFileRead(url)
        return 0, None

    def setConnection(self, dbname, password):
        url, warning = getDataSourceUrl(self.ctx, dbname, g_identifier, True)
        if warning is None:
            credential = self.getCredential(password)
            connection, warning = getDataSourceConnection(self.ctx, url, dbname, *credential)
            if warning is None:
                self._statement = connection.createStatement()
                return True
        self.Warnings = warning
        return False

    def getCredential(self, password):
        return self.Name, password

    def synchronize(self, datasource, result):
        provider = datasource.Provider
        if provider.isOffLine():
            self._setSessionMode(provider)
        if provider.isOnLine():
            datasource.synchronize()
        return result
