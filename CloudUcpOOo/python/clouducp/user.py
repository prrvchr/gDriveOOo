#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

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
        # Uri with Scheme but without a Path generate invalid user but we need
        # to return an Identifier, and raise an 'IllegalIdentifierException'
        # when ContentProvider try to get the Content...
        # (ie: ContentProvider.queryContent() -> Identifier.getContent())
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


# Procedures no more used
    # XRestUser
    def updateTitle1(self, datasource, itemid, parentid, value, default):
        result = datasource.updateTitle(self.Id, itemid, parentid, value, default)
        return self.synchronize(datasource, result)
    def updateSize1(self, datasource, itemid, parentid, size):
        print("User.updateSize() ***********************")
        result = datasource.updateSize(self.Id, itemid, parentid, size)
        return self.synchronize(datasource, result)
    def updateTrashed1(self, datasource, itemid, parentid, value, default):
        result = datasource.updateTrashed(self.Id, itemid, parentid, value, default)
        return self.synchronize(datasource, result)

    def getInputStream1(self, url):
        sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
        if sf.exists(url):
            return sf.getSize(url), sf.openFileRead(url)
        return 0, None

    def synchronize1(self, datasource, result):
        provider = datasource.Provider
        if provider.isOffLine():
            self._setSessionMode(provider)
        if provider.isOnLine():
            datasource.synchronize()
        return result
