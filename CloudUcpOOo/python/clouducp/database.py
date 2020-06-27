#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XEventListener
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE
from com.sun.star.sdb.CommandType import QUERY
from com.sun.star.ucb import XRestDataBase
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

from .configuration import g_admin

from .dbqueries import getSqlQuery
from .dbconfig import g_role

from .dbtools import checkDataBase
from .dbtools import createStaticTable
from .dbtools import executeQueries
from .dbtools import executeSqlQueries
from .dbtools import getDataSourceCall

from .dbinit import getStaticTables
from .dbinit import getQueries
from .dbinit import getTablesAndStatements

from .dbtools import getDataBaseConnection
from .dbtools import getDataSourceConnection
from .dbtools import getKeyMapFromResult
from .dbtools import getSequenceFromResult
from .dbtools import getSqlException

from .logger import logMessage
from .logger import getMessage

from collections import OrderedDict
import binascii
import traceback


class DataBase(unohelper.Base,
               XRestDataBase):
    def __init__(self, ctx, datasource, name='', password=''):
        self.ctx = ctx
        self._statement = datasource.getConnection(name, password).createStatement()
        self._CallsPool = OrderedDict()
        self._batchedCall = []

    @property
    def Connection(self):
        return self._statement.getConnection()

    def addCloseListener(self, listener):
        self.Connection.Parent.DatabaseDocument.addCloseListener(listener)

    def shutdownDataBase(self, compact=False):
        if compact:
            query = getSqlQuery('shutdownCompact')
        else:
            query = getSqlQuery('shutdown')
        self._statement.execute(query)

    def initDataBase(self, url):
        error = self.createDataBase()
        if error is None:
            self.storeDataBase(url)

    def createDataBase(self):
        try:
            print("DataBase.createDataBase() 1")
            version, error = checkDataBase(self.ctx, self._statement.getConnection())
            print("DataBase.createDataBase() 2")
            if error is None:
                print("DataBase.createDataBase() 3")
                tables = getStaticTables()
                print("DataBase.createDataBase() 4 %s" % (tables, ))
                createStaticTable(self._statement, getStaticTables(), True)
                print("DataBase.createDataBase() 5")
                tables, statements = getTablesAndStatements(self._statement, version)
                print("DataBase.createDataBase() 6")
                executeSqlQueries(self._statement, tables)
                print("DataBase.createDataBase() 7")
                self._executeQueries(getQueries())
            print("DataBase.createDataBase() 8")
            return error
        except Exception as e:
            msg = "DataBase createDataBase(): Error: %s - %s" % (e, traceback.print_exc())
            print(msg)

    def _executeQueries(self, queries):
        for name, format in queries:
            query = getSqlQuery(name, format)
            print("DataBase._executeQueries() %s" % query)
            self._statement.executeQuery(query)

    def storeDataBase(self, url):
        self._statement.getConnection().getParent().DatabaseDocument.storeAsURL(url, ())

    def createUser(self, user, password):
        name, password = user.getCredential(password)
        format = {'User': name, 'Password': password, 'RootId': user.RootId,
                  'Role': g_role, 'View': user.getViewName(), 'Admin': g_admin}
        sql = getSqlQuery('createUser', format)
        status = self._statement.executeUpdate(sql)
        sql = getSqlQuery('grantRole', format)
        status += self._statement.executeUpdate(sql)
        return status == 0

    def selectUser(self, name):
        user = None
        select = self._getDataSourceCall('getUser')
        select.setString(1, name)
        result = select.executeQuery()
        if result.next():
            user = getKeyMapFromResult(result)
        select.close()
        return user

    def insertUser(self, provider, user, root):
        userid = provider.getUserId(user)
        username = provider.getUserName(user)
        displayname = provider.getUserDisplayName(user)
        rootid = provider.getRootId(root)
        rootname = provider.getRootTitle(root)
        timestamp = parseDateTime()
        insert = self._getDataSourceCall('insertUser')
        insert.setString(1, username)
        insert.setString(2, displayname)
        insert.setString(3, rootid)
        insert.setTimestamp(4, timestamp)
        insert.setString(5, userid)
        insert.execute()
        insert.close()
        if not self._executeRootCall(provider, 'update', userid, root, timestamp):
            self._executeRootCall(provider, 'insert', userid, root, timestamp)
        data = KeyMap()
        data.insertValue('UserId', userid)
        data.insertValue('UserName', username)
        data.insertValue('RootId', rootid)
        data.insertValue('RootName', rootname)
        data.insertValue('Token', '')
        return data

    def selectItem(self, user, identifier):
        item = None
        select = self._getDataSourceCall('getItem')
        select.setString(1, user.getValue('UserId'))
        select.setString(2, identifier.getValue('Id'))
        result = select.executeQuery()
        if result.next():
            item = getKeyMapFromResult(result, KeyMap())
        select.close()
        return item

    def insertItem(self, provider, user, data):
        item = None
        separator = ','
        timestamp = parseDateTime()
        call = self._getDataSourceCall('insertItem')
        call.setString(1, user.getValue('UserId'))
        call.setString(2, separator)
        call.setLong(3, 0)
        id = provider.getItemId(data)
        parents = provider.getItemParent(data, user.getValue('RootId'))
        self._setCallItem(call, provider, data, id, parents, separator, timestamp)
        result = call.executeQuery()
        if result.next():
            item = getKeyMapFromResult(result)
        return item

    def getContentType(self):
        call = self._getDataSourceCall('getContentType')
        result = call.executeQuery()
        if result.next():
            item = getKeyMapFromResult(result)
        call.close()
        return item.getValue('Folder'), item.getValue('Link')

    def updateDrive(self, provider, user):
        timestamp = parseDateTime()
        separator = ','
        call = self._getDataSourceCall('mergeItem', True)
        call.setString(1, user.Id)
        call.setString(2, separator)
        call.setLong(3, 1)
        rootid = user.RootId
        roots = [rootid]
        rows, items, parents, page, row = self._getDriveContent(call, provider, user, rootid, roots, separator, timestamp)
        rows += self._filterParents(call, provider, items, parents, roots, separator, timestamp)
        rejected = self._getRejectedItems(provider, parents, items)
        self._closeDataSourceCall()
        return rejected, rows, page, row

    def _getDriveContent(self, call, provider, user, rootid, roots, separator, timestamp):
        rows = []
        items = {}
        childs = []
        parameter = provider.getRequestParameter('getDriveContent', user.MetaData)
        enumerator = user.Request.getIterator(parameter, None)
        while enumerator.hasMoreElements():
            item = enumerator.nextElement()
            id = provider.getItemId(item)
            parents = provider.getItemParent(item, user.RootId)
            if all(parent in roots for parent in parents):
                roots.append(id)
                rows.append(self._setCallItem(call, provider, item, id, parents, separator, timestamp))
                call.addBatch()
            else:
                items[id] = item
                childs.append((id, parents))
        page = enumerator.PageCount
        row = enumerator.RowCount
        return rows, items, childs, page, row

    def _filterParents(self, call, provider, items, childs, roots, separator, timestamp):
        i = -1
        rows = []
        while len(childs) and len(childs) != i:
            i = len(childs)
            print("datasource._filterParents() %s" % len(childs))
            for item in childs:
                id, parents = item
                if all(parent in roots for parent in parents):
                    roots.append(id)
                    rows.append(self._setCallItem(call, provider, items[id], id, parents, separator, timestamp))
                    call.addBatch()
                    childs.remove(item)
            childs.reverse()
        return rows

    def _getRejectedItems(self, provider, items, data):
        rejected = []
        for id, parents in items:
            title = provider.getItemTitle(data[id])
            rejected.append((title, id, ','.join(parents)))
        return rejected

    def _setCallItem(self, call, provider, item, id, parents, separator, timestamp):
        call.setString(4, id)
        call.setString(5, separator.join(parents))
        call.setString(6, provider.getItemTitle(item))
        call.setTimestamp(7, provider.getItemCreated(item, timestamp))
        call.setTimestamp(8, provider.getItemModified(item, timestamp))
        call.setString(9, provider.getItemMediaType(item))
        call.setLong(10, provider.getItemSize(item))
        call.setBoolean(11, provider.getItemTrashed(item))
        call.setBoolean(12, provider.getItemCanAddChild(item))
        call.setBoolean(13, provider.getItemCanRename(item))
        call.setBoolean(14, provider.getItemIsReadOnly(item))
        call.setBoolean(15, provider.getItemIsVersionable(item))
        return 1

    def updateFolderContent(self, provider, user, content):
        try:
            rows = []
            separator = ','
            timestamp = parseDateTime()
            print("datasource._updateFolderContent() 1")
            call = self._getDataSourceCall('mergeItem', True)
            print("datasource._updateFolderContent() 2")
            call.setString(1, user.Id)
            call.setString(2, separator)
            call.setLong(3, 0)
            print("datasource._updateFolderContent() 3")
            enumerator = provider.getFolderContent(user.Request, content)
            print("datasource._updateFolderContent() 4")
            while enumerator.hasMoreElements():
                item = enumerator.nextElement()
                print("datasource._updateFolderContent() 5 - %s" % (item, ))
                id = provider.getItemId(item)
                parents = provider.getItemParent(item, user.RootId)
                rows.append(self._setCallItem(call, provider, item, id, parents, separator, timestamp))
                call.addBatch()
            self._closeDataSourceCall()
            print("datasource._updateFolderContent() 6 - %s" % (rows, ))
            return all(rows)
        except Exception as e:
            print("DataBase.updateFolderContent() ERROR: %s - %s" % (e, traceback.print_exc()))

    def getChildren(self, provider, user, identifier):
        select = self._getDataSourceCall('getChildren1')
        scroll = 'com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE'
        select.ResultSetType = uno.getConstantByName(scroll)
        # OpenOffice / LibreOffice Columns:
        #    ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden',
        #    'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
        # "TargetURL" is done by:
        #    CONCAT(BaseURL,'/',Id) for Foder or CONCAT(BaseURL,'/',Title) for File.
        url = identifier.getValue('BaseURL')
        select.setString(1, url)
        select.setString(2, url)
        select.setString(3, user.getValue('UserId'))
        select.setString(4, identifier.getValue('Id'))
        select.setShort(5, provider.SessionMode)
        return select

    def getChildren1(self, provider, user, identifier):
        select = self._getDataSourceCall('getChildren')
        scroll = 'com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE'
        select.ResultSetType = uno.getConstantByName(scroll)
        # OpenOffice / LibreOffice Columns:
        #    ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden',
        #    'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
        # "TargetURL" is done by:
        #    CONCAT(BaseURL,'/',Id) for Foder or CONCAT(BaseURL,'/',Title) for File.
        select.setString(1, user.getValue('UserId'))
        select.setString(2, identifier.getValue('Id'))
        select.setString(3, identifier.getValue('BaseURL'))
        select.setShort(4, provider.SessionMode)
        return select

    def updateLoaded(self, userid, itemid, value, default):
        update = self._getDataSourceCall('updateLoaded')
        update.setLong(1, value)
        update.setString(2, itemid)
        row = update.executeUpdate()
        update.close()
        return default if row != 1 else value






    def _executeRootCall(self, provider, method, userid, root, timestamp):
        row = 0
        id = provider.getRootId(root)
        call = self._getDataSourceCall('%sItem1' % method)
        call.setString(1, provider.getRootTitle(root))
        call.setTimestamp(2, provider.getRootCreated(root, timestamp))
        call.setTimestamp(3, provider.getRootModified(root, timestamp))
        call.setString(4, provider.getRootMediaType(root))
        call.setLong(5, provider.getRootSize(root))
        call.setBoolean(6, provider.getRootTrashed(root))
        call.setString(7, id)
        row = call.executeUpdate()
        call.close()
        if row:
            call = self._getDataSourceCall('%sCapability1' % method)
            call.setBoolean(1, provider.getRootCanAddChild(root))
            call.setBoolean(2, provider.getRootCanRename(root))
            call.setBoolean(3, provider.getRootIsReadOnly(root))
            call.setBoolean(4, provider.getRootIsVersionable(root))
            call.setString(5, userid)
            call.setString(6, id)
            call.executeUpdate()
            call.close()
        return row

    def _prepareItemCall(self, provider, method, delete, insert, user, item, timestamp):
        row = 0
        userid = user.getValue('UserId')
        rootid = user.getValue('RootId')
        c1 = self._getDataSourceCall('%sItem1' % method)
        c2 = self._getDataSourceCall('%sCapability1' % method)
        row = self._executeItemCall(provider, c1, c2, delete, insert, userid, rootid, item, timestamp)
        c1.close()
        c2.close()
        return row

    def _executeItemCall(self, provider, c1, c2, c3, c4, userid, rootid, item, timestamp):
        row = 0
        id = provider.getItemId(item)
        c1.setString(1, provider.getItemTitle(item))
        c1.setTimestamp(2, provider.getItemCreated(item, timestamp))
        c1.setTimestamp(3, provider.getItemModified(item, timestamp))
        c1.setString(4, provider.getItemMediaType(item))
        c1.setLong(5, provider.getItemSize(item))
        c1.setBoolean(6, provider.getItemTrashed(item))
        c1.setString(7, id)
        row = c1.executeUpdate()
        if row:
            c2.setBoolean(1, provider.getItemCanAddChild(item))
            c2.setBoolean(2, provider.getItemCanRename(item))
            c2.setBoolean(3, provider.getItemIsReadOnly(item))
            c2.setBoolean(4, provider.getItemIsVersionable(item))
            c2.setString(5, userid)
            c2.setString(6, id)
            c2.executeUpdate()
            c3.setString(1, userid)
            c3.setString(2, id)
            c3.executeUpdate()
            c4.setString(1, userid)
            c4.setString(2, id)
            for parent in provider.getItemParent(item, rootid):
                c4.setString(3, parent)
                c4.executeUpdate()
        return row

    def _updateItem(self, provider, c1, c2, c3, c4, c5, c6, userid, rootid, item, timestamp):
        row = self._executeItemCall(provider, c1, c2, c5, c6, userid, rootid, item, timestamp)
        if not row:
            row = self._executeItemCall(provider, c3, c4, c5, c6, userid, rootid, item, timestamp)
        return row

    def setSyncToken(self, provider, user):
        data = provider.getToken(user.Request, user.MetaData)
        if data.IsPresent:
            token = provider.getUserToken(data.Value)
            self._updateToken(user.MetaData, token)

    def _updateToken(self, user, token):
        update = self._getDataSourceCall('updateToken')
        update.setString(1, token)
        update.setString(2, user.getValue('UserId'))
        updated = update.executeUpdate() == 1
        update.close()
        if updated:
            user.setValue('Token', token)

    def checkNewIdentifier(self, provider, request, user):
        if provider.isOffLine() or not provider.GenerateIds:
            return
        result = False
        if self._countIdentifier(user) < min(provider.IdentifierRange):
            result = self._insertIdentifier(provider, request, user)
        return

    def getNewIdentifier(self, provider, user):
        if provider.GenerateIds:
            id = ''
            select = self._getDataSourceCall('getNewIdentifier')
            select.setString(1, user.getValue('UserId'))
            result = select.executeQuery()
            if result.next():
                id = result.getString(1)
            select.close()
        else:
            id = binascii.hexlify(uno.generateUuid().value).decode('utf-8')
        return id

    def _countIdentifier(self, user):
        count = 0
        call = self._getDataSourceCall('countNewIdentifier')
        call.setString(1, user.getValue('UserId'))
        result = call.executeQuery()
        if result.next():
            count = result.getLong(1)
        call.close()
        return count

    def _insertIdentifier(self, provider, request, user):
        result = []
        enumerator = provider.getIdentifier(request, user)
        insert = self._getDataSourceCall('insertIdentifier')
        insert.setString(1, user.getValue('UserId'))
        while enumerator.hasMoreElements():
            item = enumerator.nextElement()
            print("datasource._insertIdentifier() %s" % (item, ))
            result.append(self._doInsert(insert, item))
        insert.close()
        return all(result)

    def _doInsert(self, insert, id):
        insert.setString(2, id)
        return insert.executeUpdate()

    def getItemToSync(self, provider, user):
        items = []
        select = self._getDataSourceCall('getItemToSync')
        select.setString(1, user.getValue('UserId'))
        result = select.executeQuery()
        while result.next():
            items.append(getKeyMapFromResult(result, user, provider))
        select.close()
        msg = "Items to Sync: %s" % len(items)
        logMessage(self.ctx, INFO, msg, "DataSource", "_getItemToSync()")
        return tuple(items)

    def syncItem(self, provider, request, uploader, item):
        try:
            response = False
            mode = item.getValue('Mode')
            sync = item.getValue('SyncId')
            id = item.getValue('Id')
            msg = "SyncId - ItemId - Mode: %s - %s - %s" % (sync, id, mode)
            logMessage(self.ctx, INFO, msg, "DataSource", "_syncItem()")
            if mode == SYNC_FOLDER:
                response = provider.createFolder(request, item)
            elif mode == SYNC_FILE:
                response = provider.createFile(request, uploader, item)
            elif mode == SYNC_CREATED:
                response = provider.uploadFile(request, uploader, item, True)
            elif mode == SYNC_REWRITED:
                response = provider.uploadFile(request, uploader, item, False)
            elif mode == SYNC_RENAMED:
                response = provider.updateTitle(request, item)
            elif mode == SYNC_TRASHED:
                response = provider.updateTrashed(request, item)
            return response
        except Exception as e:
            msg = "SyncId: %s - ERROR: %s - %s" % (sync, e, traceback.print_exc())
            logMessage(self.ctx, SEVERE, msg, "DataSource", "_syncItem()")

    def callBack(self, provider, item, response):
        if response.IsPresent:
            self.updateSync(provider, item, response.Value)

    def updateSync(self, provider, item, response):
        oldid = item.getValue('Id')
        newid = provider.getResponseId(response, oldid)
        oldname = item.getValue('Title')
        newname = provider.getResponseTitle(response, oldname)
        delete = self._getDataSourceCall('deleteSyncMode')
        delete.setLong(1, item.getValue('SyncId'))
        row = delete.executeUpdate()
        msg = "execute deleteSyncMode OldId: %s - NewId: %s - Row: %s" % (oldid, newid, row)
        logMessage(self.ctx, INFO, msg, "DataSource", "updateSync")
        delete.close()
        if row and newid != oldid:
            update = self._getDataSourceCall('updateItemId')
            update.setString(1, newid)
            update.setString(2, oldid)
            row = update.executeUpdate()
            msg = "execute updateItemId OldId: %s - NewId: %s - Row: %s" % (oldid, newid, row)
            logMessage(self.ctx, INFO, msg, "DataSource", "updateSync")
            update.close()
        return '' if row != 1 else newid

    def insertNewDocument(self, provider, userid, itemid, parentid, content):
        modes = provider.FileSyncModes
        inserted = self._insertNewContent(userid, itemid, parentid, content, modes)
        if inserted:
            self.event.set()
        return inserted

    def insertNewFolder(self, provider, userid, itemid, parentid, content):
        modes = provider.FolderSyncModes
        inserted = self._insertNewContent(userid, itemid, parentid, content, modes)
        if inserted:
            self.event.set()
        return inserted

    def _insertNewContent(self, userid, itemid, parentid, content, modes):
        c1 = self._getDataSourceCall('insertItem1')
        c1.setString(1, content.getValue("Title"))
        c1.setTimestamp(2, content.getValue('DateCreated'))
        c1.setTimestamp(3, content.getValue('DateModified'))
        c1.setString(4, content.getValue('MediaType'))
        c1.setLong(5, content.getValue('Size'))
        c1.setBoolean(6, content.getValue('Trashed'))
        c1.setString(7, itemid)
        row = c1.executeUpdate()
        c1.close()
        c2 = self._getDataSourceCall('insertCapability1')
        c2.setBoolean(1, content.getValue('CanAddChild'))
        c2.setBoolean(2, content.getValue('CanRename'))
        c2.setBoolean(3, content.getValue('IsReadOnly'))
        c2.setBoolean(4, content.getValue('IsVersionable'))
        c2.setString(5, userid)
        c2.setString(6, itemid)
        row += c2.executeUpdate()
        c2.close()
        c3 = self._getDataSourceCall('insertParent1')
        c3.setString(1, userid)
        c3.setString(2, itemid)
        c3.setString(3, parentid)
        row += c3.executeUpdate()
        c3.close()
        c4 = self._getDataSourceCall('insertSyncMode')
        c4.setString(1, userid)
        c4.setString(2, itemid)
        c4.setString(3, parentid)
        for mode in modes:
            c4.setLong(4, mode)
            row += c4.execute()
        c4.close()
        return row == 3 + len(modes)

    def updateTitle(self, userid, itemid, parentid, value, default):
        row = 0
        update = self._getDataSourceCall('updateTitle')
        update.setString(1, value)
        update.setString(2, itemid)
        if update.executeUpdate():
            insert = self._getDataSourceCall('insertSyncMode')
            insert.setString(1, userid)
            insert.setString(2, itemid)
            insert.setString(3, parentid)
            insert.setLong(4, SYNC_RENAMED)
            row = insert.executeUpdate()
            insert.close()
        update.close()
        return default if row != 1 else value

    def updateSize(self, userid, itemid, parentid, size):
        row = 0
        update = self._getDataSourceCall('updateSize')
        update.setLong(1, size)
        update.setString(2, itemid)
        if update.executeUpdate():
            insert = self._getDataSourceCall('insertSyncMode')
            insert.setString(1, userid)
            insert.setString(2, itemid)
            insert.setString(3, parentid)
            insert.setLong(4, SYNC_REWRITED)
            row = insert.executeUpdate()
            insert.close()
        update.close()
        return None if row != 1 else size

    def updateTrashed(self, userid, itemid, parentid, value, default):
        row = 0
        update = self._getDataSourceCall('updateTrashed')
        update.setLong(1, value)
        update.setString(2, itemid)
        if update.executeUpdate():
            insert = self._getDataSourceCall('insertSyncMode')
            insert.setString(1, userid)
            insert.setString(2, itemid)
            insert.setString(3, parentid)
            insert.setLong(4, SYNC_TRASHED)
            row = insert.executeUpdate()
            insert.close()
        update.close()
        return default if row != 1 else value

    def isChildId(self, userid, itemid, title):
        ischild = False
        call = self._getDataSourceCall('isChildId')
        call.setString(1, userid)
        call.setString(2, itemid)
        call.setString(3, title)
        result = call.executeQuery()
        if result.next():
            ischild = result.getBoolean(1)
        call.close()
        return ischild

    def countChildTitle(self, userid, parent, title):
        count = 1
        call = self._getDataSourceCall('countChildTitle')
        call.setString(1, userid)
        call.setString(2, parent)
        call.setString(3, title)
        result = call.executeQuery()
        if result.next():
            count = result.getLong(1)
        call.close()
        return count

    # User.initializeIdentifier() helper
    def selectChildId(self, userid, parent, basename):
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
    def isIdentifier(self, userid, id):
        isit = False
        call = self._getDataSourceCall('isIdentifier')
        call.setString(1, id)
        result = call.executeQuery()
        if result.next():
            isit = result.getBoolean(1)
        call.close()
        return isit

    def _getDataSourceCall(self, key, batched=False, name=None, format=None):
        name = key if name is None else name
        if key in self._CallsPool:
            call = self._CallsPool[key]
        elif batched:
            call = getDataSourceCall(self.Connection, name, format)
            self._CallsPool[key] = call
        else:
            call = getDataSourceCall(self.Connection, name, format)
        if batched and key not in self._batchedCall:
            self._batchedCall.append(key)
        return call

    def _getPreparedCall(self, name):
        if name not in self._CallsPool:
            # TODO: cannot use: call = self.Connection.prepareCommand(name, QUERY)
            # TODO: it trow a: java.lang.IncompatibleClassChangeError
            #query = self.Connection.getQueries().getByName(name).Command
            #self._CallsPool[name] = self.Connection.prepareCall(query)
            self._CallsPool[name] = self.Connection.prepareCommand(name, QUERY)
        if name not in self._batchedCall:
            self._batchedCall.append(name)
        return self._CallsPool[name]

    def _executeBatchCall(self):
        for name in self._batchedCall:
            self._CallsPool[name].executeBatch()
        self._batchedCall = []

    def _closeDataSourceCall(self):
        for name in self._CallsPool:
            call = self._CallsPool[name]
            if name in self._batchedCall:
                call.executeBatch()
            call.close()
        self._CallsPool = OrderedDict()
        self._batchedCall = []
