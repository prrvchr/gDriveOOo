#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XEventListener
from com.sun.star.util import XCloseListener

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE
from com.sun.star.sdb.CommandType import QUERY
from com.sun.star.ucb import XRestDataSource
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_RETRIEVED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_CREATED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_FOLDER
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_FILE
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_RENAMED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_REWRITED
from com.sun.star.ucb.RestDataSourceSyncMode import SYNC_TRASHED

from unolib import KeyMap
from unolib import g_oauth2
from unolib import createService
from unolib import parseDateTime
from unolib import getResourceLocation
from unolib import getSimpleFile

from .configuration import g_admin
from .user import User
from .replicator import Replicator
from .database import DataBase

from .dbqueries import getSqlQuery

from .dbconfig import g_path

from .dbtools import getDataSource
from .dbtools import getDataBaseConnection
from .dbtools import getDataSourceConnection
from .dbtools import getKeyMapFromResult
from .dbtools import getSequenceFromResult
from .dbtools import getSqlException

from .logger import logMessage
from .logger import getMessage

import binascii
import traceback

from threading import Event

class DataSource(unohelper.Base,
                 XRestDataSource,
                 XCloseListener):
    def __init__(self, ctx, event, scheme, plugin):
        try:
            msg = "DataSource for Scheme: %s loading ... " % scheme
            print("DataSource __init__() 1")
            self.ctx = ctx
            self.scheme = scheme
            self.plugin = plugin
            self._CahedUser = {}
            self._Calls = {}
            self.Error = None
            self.sync = event
            self.Provider = createService(self.ctx, '%s.Provider' % plugin)
            print("DataSource __init__() 2")
            self.datasource, url, created = getDataSource(self.ctx, scheme, plugin, True)
            print("DataSource __init__() 3 %s" % created)
            self.DataBase = DataBase(self.ctx, self.datasource)
            if created:
                self.Error = self.DataBase.createDataBase()
                if self.Error is None:
                    self.DataBase.storeDataBase(url)
            self.DataBase.addCloseListener(self)
            folder, link = self.DataBase.getContentType()
            self.Provider.initialize(scheme, plugin, folder, link)
            self.replicator = Replicator(ctx, self.datasource, self.Provider, self._CahedUser, self.sync)
            print("DataSource __init__() 4")
            logMessage(self.ctx, INFO, "stage 2", 'DataSource', '__init__()')
            print("DataSource __init__() 5")
            msg += "Done"
            logMessage(self.ctx, INFO, msg, 'DataSource', '__init__()')
        except Exception as e:
            msg = "DataSource __init__(): Error: %s - %s" % (e, traceback.print_exc())
            print(msg)

    # XCloseListener
    def queryClosing(self, source, ownership):
        print("DataSource.queryClosing() 1")
        if self.replicator.is_alive():
            self.replicator.cancel()
            print("DataSource.queryClosing() 2")
            self.replicator.join()
        #self.deregisterInstance(self.Scheme, self.Plugin)
        self.DataBase.shutdownDataBase()
        msg = "DataSource queryClosing: Scheme: %s ... Done" % self.scheme
        logMessage(self.ctx, INFO, msg, 'DataSource', 'queryClosing()')
        print("DataSource.queryClosing() 3 OK")
    def notifyClosing(self, source):
        pass

    # XRestDataSource
    def isValid(self):
        return self.Error is None

    def getUser(self, name, password=''):
        print("DataSource.getUser() 1")
        # User never change... we can cache it...
        if name in self._CahedUser:
            print("DataSource.getUser() 3")
            user = self._CahedUser[name]
        else:
            print("DataSource.getUser() 4")
            user = User(self.ctx, self, name)
            print("DataSource.getUser() 5")
            if not self._initializeUser(user, name, password):
                print("DataSource.getUser() 6 ERROR")
                return None
            self._CahedUser[name] = user
            print("DataSource.getUser() 7")
            self.sync.set()
        print("DataSource.getUser() 8")
        return user

    def getRequest(self, name):
        request = createService(self.ctx, g_oauth2)
        if request is not None:
            request.initializeSession(self.Provider.Scheme, name)
        return request

    def _initializeUser(self, user, name, password):
        if user.Request is not None:
            if user.MetaData is not None:
                user.setDataBase(self.datasource, password, self.sync)
                return True
            if self.Provider.isOnLine():
                data = self.Provider.getUser(user.Request, name)
                if data.IsPresent:
                    root = self.Provider.getRoot(user.Request, data.Value)
                    if root.IsPresent:
                        user.MetaData = self.DataBase.insertUser(user.Provider, data.Value, root.Value)
                        if self.DataBase.createUser(user, password):
                            user.setDataBase(self.datasource, password, self.sync)
                            return True
                        else:
                            self.Error = getMessage(self.ctx, 1106, name)
                    else:
                        self.Error = getMessage(self.ctx, 1107, name)
                else:
                    self.Error = getMessage(self.ctx, 1107, name)
            else:
                self.Error = getMessage(self.ctx, 1108, name)
        else:
            self.Error = getMessage(self.ctx, 1105, g_oauth2)
        return False


# Procedures no more used
    def getItemToSync1(self, user):
        items = []
        select = self._getDataSourceCall('getItemToSync')
        select.setString(1, user.getValue('UserId'))
        result = select.executeQuery()
        while result.next():
            items.append(getKeyMapFromResult(result, user, self.Provider))
        select.close()
        msg = "Items to Sync: %s" % len(items)
        logMessage(self.ctx, INFO, msg, "DataSource", "_getItemToSync()")
        return tuple(items)

    def syncItem1(self, request, uploader, item):
        try:
            response = False
            mode = item.getValue('Mode')
            sync = item.getValue('SyncId')
            id = item.getValue('Id')
            msg = "SyncId - ItemId - Mode: %s - %s - %s" % (sync, id, mode)
            logMessage(self.ctx, INFO, msg, "DataSource", "_syncItem()")
            if mode == SYNC_FOLDER:
                response = self.Provider.createFolder(request, item)
            elif mode == SYNC_FILE:
                response = self.Provider.createFile(request, uploader, item)
            elif mode == SYNC_CREATED:
                response = self.Provider.uploadFile(request, uploader, item, True)
            elif mode == SYNC_REWRITED:
                response = self.Provider.uploadFile(request, uploader, item, False)
            elif mode == SYNC_RENAMED:
                response = self.Provider.updateTitle(request, item)
            elif mode == SYNC_TRASHED:
                response = self.Provider.updateTrashed(request, item)
            return response
        except Exception as e:
            msg = "SyncId: %s - ERROR: %s - %s" % (sync, e, traceback.print_exc())
            logMessage(self.ctx, SEVERE, msg, "DataSource", "_syncItem()")

    # User.initializeIdentifier() helper
    def selectChildId1(self, userid, parent, basename):
        id = ''
        call = self._getDataSourceCall('getChildId')
        call.setString(1, userid)
        call.setString(2, parent)
        call.setString(3, basename)
        result = call.executeQuery()
        if result.next():
            id = result.getString(1)
        call.close()
        return id

    # User.initializeIdentifier() helper
    def isIdentifier1(self, userid, id):
        isit = False
        call = self._getDataSourceCall('isIdentifier')
        call.setString(1, id)
        result = call.executeQuery()
        if result.next():
            isit = result.getBoolean(1)
        call.close()
        return isit

    def synchronize1(self):
        try:
            print("DataSource.synchronize() 1")
            results = []
            for user in self._CahedUser.values():
                uploader = user.Request.getUploader(self)
                for item in self.getItemToSync(user.MetaData):
                    response = self.syncItem(user.Request, uploader, item)
                    if response is None:
                        results.append(True)
                    elif response and response.IsPresent:
                        results.append(self.updateSync(item, response.Value))
                    else:
                        msg = "ERROR: ItemId: %s" % item.getDefaultValue('Id')
                        logMessage(self.ctx, SEVERE, msg, "DataSource", "synchronize()")
                        results.append(False)
            result = all(results)
            print("DataSource.synchronize() 2 %s" % result)
        except Exception as e:
            print("DataSource.synchronize() ERROR: %s - %s" % (e, traceback.print_exc()))
