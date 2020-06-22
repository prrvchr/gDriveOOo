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

from .configuration import g_sync

from .logger import logMessage
from .logger import getMessage

from threading import Thread
import traceback


class Replicator(unohelper.Base,
                 XCancellable,
                 Thread):
    def __init__(self, ctx, datasource):
        Thread.__init__(self)
        self.ctx = ctx
        self.datasource = datasource
        self.canceled = False
        datasource.event.clear()
        self.start()

    # XCancellable
    def cancel(self):
        self.canceled = True
        self.datasource.event.set()
        self.join()

    def run(self):
        print("replicator.run() 1 *************************************************************")
        while not self.canceled:
            self.datasource.event.wait(g_sync)
            self._synchronize()
            self.datasource.event.clear()
            print("replicator.run() 2")
        print("replicator.run() 3 *************************************************************")

    def _synchronize(self):
        if self.datasource.Provider.isOffLine():
            msg = getMessage(self.ctx, 111)
            logMessage(self.ctx, INFO, msg, 'Replicator', '_synchronize()')
        elif not self.canceled:
            timestamp = getDateTime(False)
            self._syncData(timestamp)

    def _syncData(self, timestamp):
        try:
            print("Replicator.synchronize() 1")
            results = []
            for user in self.datasource._CahedUser.values():
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
        rejected, rows, page, row = self.datasource.updateDrive(user.Request, user.MetaData)
        print("Replicator._initData() %s - %s - %s - %s" % (len(rows), all(rows), page, row))
        msg = getMessage(self.ctx, 120, (page, row, len(rows)))
        logMessage(self.ctx, INFO, msg, 'Replicator', '_syncData()')
        if len(rejected):
            msg = getMessage(self.ctx, 121, len(rejected))
            logMessage(self.ctx, SEVERE, msg, 'Replicator', '_syncData()')
        for item in rejected:
            msg = getMessage(self.ctx, 122, item)
            logMessage(self.ctx, SEVERE, msg, 'Replicator', '_syncData()')
        if all(rows):
            self.datasource.setSyncToken(user.Request, user.MetaData)

    def _pullData(self, user):
        results = []
        self.datasource.checkNewIdentifier(user.Request, user.MetaData)
        print("Replicator._pullData() 1")
        parameter = self.datasource.Provider.getRequestParameter('getChanges', user.MetaData)
        enumerator = user.Request.getIterator(parameter, None)
        print("Replicator._pullData() 2 %s - %s" % (enumerator.PageCount, enumerator.SyncToken))
        while enumerator.hasMoreElements():
            response = enumerator.nextElement()
            print("Replicator._pullData() 3 %s" % response)
        print("Replicator._pullData() 4 %s - %s" % (enumerator.PageCount, enumerator.SyncToken))
        return results

    def _pushData(self, user):
        results = []
        uploader = user.Request.getUploader(self.datasource)
        for item in self.datasource.getItemToSync(user.MetaData):
            if self.canceled:
                break
            response = self.datasource.syncItem(user.Request, uploader, item)
            if response is None:
                results.append(True)
            elif response and response.IsPresent:
                results.append(self.datasource.updateSync(item, response.Value))
            else:
                msg = "ERROR: ItemId: %s" % item.getDefaultValue('Id')
                logMessage(self.ctx, SEVERE, msg, "Replicator", "_pushData()")
                results.append(False)
        return results
