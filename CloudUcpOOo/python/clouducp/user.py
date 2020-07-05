#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE

from com.sun.star.ucb import XRestUser

from .database import DataBase
from .logger import logMessage
from .logger import getMessage

import traceback


class User(unohelper.Base,
           XRestUser):
    def __init__(self, ctx, datasource, name, error=None):
        msg = "User loading"
        self.ctx = ctx
        self.DataBase = None
        self.Error = error
        # Incomplete Url generate invalid User
        if self.isValid():
            self.Request = datasource.getRequest(name)
            self.MetaData = datasource.DataBase.selectUser(name)
            self.Provider = datasource.Provider
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

    def isValid(self):
        return self.Error is None

    def setDataBase(self, datasource, password, sync):
        name, password = self.getCredential(password)
        self.DataBase = DataBase(self.ctx, datasource, name, password, sync)

    def getCredential(self, password):
        return self.Name, password






    def getItem(self, datasource, identifier):
        item = self.DataBase.selectItem(self.MetaData, identifier)
        if item is None and self.Provider.isOnLine():
            data = self.Provider.getItem(self.Request, identifier)
            if data.IsPresent:
                item = self.DataBase.insertAndSelectItem(self.MetaData, data.Value)
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

    def getViewName(self):
        return self.Name.split('@').pop(0)

    def synchronize(self, datasource, result):
        provider = datasource.Provider
        if provider.isOffLine():
            self._setSessionMode(provider)
        if provider.isOnLine():
            datasource.synchronize()
        return result
