#!
# -*- coding: utf_8 -*-

#from __futur__ import absolute_import

import uno
import unohelper

from com.sun.star.util import XCancellable
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from unolib import KeyMap
from unolib import getDateTime
from unolib import unparseTimeStamp

from .configuration import g_sync
from .database import DataBase

from .dbinit import getDataSourceUrl
from .dbinit import createDataBase

from .dbtools import getDataSourceConnection
from .dbtools import createDataSource
from .dbtools import registerDataSource

from .logger import logMessage
from .logger import getMessage

from threading import Thread
import traceback
import time

class Replicator(unohelper.Base,
                 XCancellable,
                 Thread):
    def __init__(self, ctx, datasource, provider, users, sync):
        Thread.__init__(self)
        self.ctx = ctx
        self.database = DataBase(self.ctx, datasource)
        self.provider = provider
        self.users = users
        self.canceled = False
        self.sync = sync
        sync.clear()
        self.error = None
        self.start()

    # XCancellable
    def cancel(self):
        self.canceled = True
        self.sync.set()
        self.join()

    def run(self):
        try:
            msg = "Replicator for Scheme: %s loading ... " % self.provider.Scheme
            print("Replicator.run() 1 *************************************************************")
            logMessage(self.ctx, INFO, "stage 1", 'Replicator', 'run()')
            print("Replicator run() 2")
            while not self.canceled:
                self.sync.wait(g_sync)
                self._synchronize()
                self.sync.clear()
                print("replicator.run() 3")
            print("replicator.run() 4 *************************************************************")
        except Exception as e:
            msg = "Replicator run(): Error: %s - %s" % (e, traceback.print_exc())
            print(msg)

    def _synchronize(self):
        if self.provider.isOffLine():
            msg = getMessage(self.ctx, 111)
            logMessage(self.ctx, INFO, msg, 'Replicator', '_synchronize()')
        elif not self.canceled:
            timestamp = getDateTime(False)
            self._syncData(timestamp)

    def _syncData(self, timestamp):
        try:
            print("Replicator.synchronize() 1")
            results = []
            for user in self.users.values():
                if self.canceled:
                    break
                msg = getMessage(self.ctx, 110, user.Name)
                logMessage(self.ctx, INFO, msg, 'Replicator', '_syncData()')
                if not user.Token:
                    self._initUser(user)
                if user.Token:
                    results += self._pullData(user)
                    results += self._pushData(user)
                msg = getMessage(self.ctx, 116, user.Name)
                logMessage(self.ctx, INFO, msg, 'Replicator', '_syncData()')
            result = all(results)
            print("Replicator.synchronize() 2 %s" % result)
        except Exception as e:
            print("Replicator.synchronize() ERROR: %s - %s" % (e, traceback.print_exc()))

    def _initUser(self, user):
        rejected, rows, page, row = self.database.updateDrive(self.provider, user)
        print("Replicator._initUser() 1 %s - %s - %s - %s" % (len(rows), all(rows), page, row))
        msg = getMessage(self.ctx, 120, (page, row, len(rows)))
        logMessage(self.ctx, INFO, msg, 'Replicator', '_syncData()')
        if len(rejected):
            msg = getMessage(self.ctx, 121, len(rejected))
            logMessage(self.ctx, SEVERE, msg, 'Replicator', '_syncData()')
        for item in rejected:
            msg = getMessage(self.ctx, 122, item)
            logMessage(self.ctx, SEVERE, msg, 'Replicator', '_syncData()')
        if all(rows):
            self.database.setSyncToken(self.provider, user)
        print("Replicator._initUser() 2 %s" % (all(rows), ))

    def _pullData(self, user):
        results = []
        self.database.checkNewIdentifier(self.provider, user.Request, user.MetaData)
        print("Replicator._pullData() 1")
        parameter = self.provider.getRequestParameter('getChanges', user.MetaData)
        enumerator = user.Request.getIterator(parameter, None)
        print("Replicator._pullData() 2 %s - %s" % (enumerator.PageCount, enumerator.SyncToken))
        while enumerator.hasMoreElements():
            response = enumerator.nextElement()
            print("Replicator._pullData() 3 %s" % response)
        print("Replicator._pullData() 4 %s - %s" % (enumerator.PageCount, enumerator.SyncToken))
        return results

    def _pushData(self, user):
        results = []
        self.database.getChangedItems1(user.Id)
        self.database.getChangedItems(user.Id)
        return results

    def _pushData1(self, user):
        results = []
        uploader = user.Request.getUploader(self.database)
        for item in self.database.getItemToSync(user.MetaData):
            if self.canceled:
                break
            response = self.database.syncItem(user.Request, uploader, item)
            if response is None:
                results.append(True)
            elif response and response.IsPresent:
                results.append(self.database.updateSync(item, response.Value))
            else:
                msg = "ERROR: ItemId: %s" % item.getDefaultValue('Id')
                logMessage(self.ctx, SEVERE, msg, "Replicator", "_pushData()")
                results.append(False)
        return results
