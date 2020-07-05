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
from unolib import getDateTime
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
    def __init__(self, ctx, datasource, name='', password='', sync=None):
        self.ctx = ctx
        self._statement = datasource.getConnection(name, password).createStatement()
        self._CallsPool = OrderedDict()
        self._batchedCall = []
        if sync is not None:
            self.sync = sync

    @property
    def Connection(self):
        return self._statement.getConnection()


# Procedures called by the DataSource
    def addCloseListener(self, listener):
        self.Connection.Parent.DatabaseDocument.addCloseListener(listener)

    def shutdownDataBase(self, compact=False):
        if compact:
            query = getSqlQuery('shutdownCompact')
        else:
            query = getSqlQuery('shutdown')
        self._statement.execute(query)

    def initDataBase(self, url):
        error = self._createDataBase()
        if error is None:
            self._storeDataBase(url)

    def _createDataBase(self):
        version, error = checkDataBase(self.ctx, self._statement.getConnection())
        print("DataBase.createDataBase() Hsqldb Version: %s" % version)
        if error is None:
            createStaticTable(self._statement, getStaticTables(), True)
            tables, statements = getTablesAndStatements(self._statement, version)
            executeSqlQueries(self._statement, tables)
            self._executeQueries(getQueries())
        return error

    def _executeQueries(self, queries):
        for name, format in queries:
            query = getSqlQuery(name, format)
            print("DataBase._executeQueries() %s" % query)
            self._statement.executeQuery(query)

    def _storeDataBase(self, url):
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
        self._mergeRoot(provider, userid, rootid, rootname, root, timestamp)
        data = KeyMap()
        data.insertValue('UserId', userid)
        data.insertValue('UserName', username)
        data.insertValue('RootId', rootid)
        data.insertValue('RootName', rootname)
        data.insertValue('Token', '')
        return data

    def _mergeRoot(self, provider, userid, rootid, rootname, root, timestamp):
        call = self._getDataSourceCall('mergeItem')
        call.setString(1, userid)
        call.setString(2, ',')
        call.setLong(3, 0)
        call.setString(4, rootid)
        call.setString(5, rootname)
        call.setTimestamp(6, provider.getRootCreated(root, timestamp))
        call.setTimestamp(7, provider.getRootModified(root, timestamp))
        call.setString(8, provider.getRootMediaType(root))
        call.setLong(9, provider.getRootSize(root))
        call.setBoolean(10, provider.getRootTrashed(root))
        call.setBoolean(11, provider.getRootCanAddChild(root))
        call.setBoolean(12, provider.getRootCanRename(root))
        call.setBoolean(13, provider.getRootIsReadOnly(root))
        call.setBoolean(14, provider.getRootIsVersionable(root))
        call.setString(15, '')
        call.executeUpdate()
        call.close()

    def getContentType(self):
        call = self._getDataSourceCall('getContentType')
        result = call.executeQuery()
        if result.next():
            item = getKeyMapFromResult(result)
        call.close()
        return item.getValue('Folder'), item.getValue('Link')


# Procedures called by the User
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

    def insertAndSelectItem(self, provider, user, data):
        item = None
        separator = ','
        timestamp = parseDateTime()
        call = self._getDataSourceCall('insertAndSelectItem')
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

    def getFolderContent(self, identifier, content, updated):
        if ONLINE == content.getValue('Loaded') == identifier.User.Provider.SessionMode:
            print("DataBase.getFolderContent() whith request")
            updated = self._updateFolderContent(identifier.User, content)
        else:
            print("DataBase.getFolderContent() no request")
        select = self._getChildren(identifier)
        return select, updated

    def _updateFolderContent(self, user, content):
        rows = []
        separator = ','
        timestamp = parseDateTime()
        call = self._getDataSourceCall('mergeItem', True)
        call.setString(1, user.Id)
        call.setString(2, separator)
        call.setLong(3, 0)
        enumerator = user.Provider.getFolderContent(user.Request, content)
        while enumerator.hasMoreElements():
            item = enumerator.nextElement()
            id = user.Provider.getItemId(item)
            parents = user.Provider.getItemParent(item, user.RootId)
            rows.append(self._setCallItem(call, user.Provider, item, id, parents, separator, timestamp))
            call.addBatch()
        self._closeDataSourceCall()
        print("DataBase._updateFolderContent() %s - %s" % (all(rows), len(rows)))
        return all(rows)

    def _getChildren(self, identifier):
        #TODO: Can't have a ResultSet of type SCROLL_INSENSITIVE with a Procedure,
        #TODO: as a workaround we use a simple quey...
        select = self._getDataSourceCall('getChildren1')
        scroll = 'com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE'
        select.ResultSetType = uno.getConstantByName(scroll)
        # OpenOffice / LibreOffice Columns:
        #    ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden',
        #    'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
        # "TargetURL" is done by:
        #    CONCAT(identifier.getContentIdentifier(), Uri) for File and Foder
        url = identifier.getContentIdentifier()
        if not url.endswith('/'):
            url += '/'
        select.setString(1, url)
        select.setString(2, identifier.User.Id)
        select.setString(3, identifier.Id)
        select.setShort(4, identifier.User.Provider.SessionMode)
        return select

    def updateLoaded(self, userid, itemid, value, default):
        update = self._getDataSourceCall('updateLoaded')
        update.setLong(1, value)
        update.setString(2, itemid)
        row = update.executeUpdate()
        update.close()
        return default if row != 1 else value

    def getIdentifier(self, user, uri, new):
        identifier = KeyMap()
        if not user.isValid():
            # Uri with Scheme but without a Path generate invalid user but we need
            # to return an Identifier, and raise an 'IllegalIdentifierException'
            # when ContentProvider try to get the Content...(ie: Identifier.getContent())
            return identifier
        call = self._getDataSourceCall('getIdentifier')
        call.setString(1, user.Id)
        call.setString(2, user.RootId)
        call.setString(3, uri.getPath())
        print("DataBase.getIdentifier() %s - %s - %s" % (user.Id, user.RootId, uri.getPath()))
        call.setString(4, '/')
        call.execute()
        id = call.getString(5)
        parentid = call.getString(6)
        path = call.getString(7)
        call.close()
        if new:
            # New Identifier are created by the parent folder...
            identifier.setValue('Id', self._getNewIdentifier(user))
            identifier.setValue('ParentId', id)
            baseuri = uri.getUriReference()
        else:
            identifier.setValue('Id', id)
            identifier.setValue('ParentId', parentid)
            baseuri = '%s://%s/%s' % (uri.getScheme(), uri.getAuthority(), path)
        identifier.setValue('BaseURI', baseuri)
        return identifier

    def _getNewIdentifier(self, user):
        if user.Provider.GenerateIds:
            id = ''
            select = self._getDataSourceCall('getNewIdentifier')
            select.setString(1, user.Id)
            result = select.executeQuery()
            if result.next():
                id = result.getString(1)
            select.close()
        else:
            id = binascii.hexlify(uno.generateUuid().value).decode('utf-8')
        return id

    def updateContent(self, userid, itemid, property, value):
        try:
            print("DataBase.updateContent() 1 %s" % property)
            if property == 'Title':
                print("DataBase.updateContent() 2")
                update = self._getDataSourceCall('updateTitle')
                print("DataBase.updateContent() 3")
                update.setString(1, userid)
                print("DataBase.updateContent() 4")
                update.setString(2, itemid)
                print("DataBase.updateContent() 5 %s" % value)
                update.setString(3, value)
                print("DataBase.updateContent() 6")
                update.execute()
                update.close()
                self.sync.set()
            elif property == 'Size':
                update = self._getDataSourceCall('updateSize')
                update.setLong(1, value)
                update.setString(2, itemid)
                update.executeUpdate()
                update.close()
                self.sync.set()
            elif property == 'Trashed':
                update = self._getDataSourceCall('updateTrashed')
                update.setBoolean(1, value)
                update.setString(2, itemid)
                update.executeUpdate()
                update.close()
                self.sync.set()
            print("DataBase.updateContent() OK")
        except Exception as e:
            msg += " ERROR: %s" % e
            print(msg)





    def getItem(self, userid, itemid):
        item = None
        select = self._getDataSourceCall('getItem')
        select.setString(1, userid)
        select.setString(2, itemid)
        result = select.executeQuery()
        if result.next():
            item = getKeyMapFromResult(result)
        select.close()
        return item

    def insertNewDocument(self, provider, userid, itemid, parentid, content):
        inserted = self._insertNewContent(userid, itemid, parentid, content)
        if inserted:
            self.event.set()
        return inserted

    def insertNewFolder(self, provider, userid, itemid, parentid, content):
        inserted = self._insertNewContent(userid, itemid, parentid, content)
        if inserted:
            self.event.set()
        return inserted

    def insertNewContent(self, userid, itemid, parentid, content):
        if self._insertNewContent(userid, itemid, parentid, content):
            # Start Replicator for uploading changes...
            self.sync.set()

    def _insertNewContent(self, userid, itemid, parentid, content):
        call = self._getDataSourceCall('insertItem')
        call.setString(1, userid)
        call.setString(2, ',')
        call.setLong(3, 1)
        call.setString(4, itemid)
        call.setString(5, content.getValue("Title"))
        call.setTimestamp(6, content.getValue('DateCreated'))
        call.setTimestamp(7, content.getValue('DateModified'))
        call.setString(8, content.getValue('MediaType'))
        call.setLong(9, content.getValue('Size'))
        call.setBoolean(10, content.getValue('Trashed'))
        call.setBoolean(11, content.getValue('CanAddChild'))
        call.setBoolean(12, content.getValue('CanRename'))
        call.setBoolean(13, content.getValue('IsReadOnly'))
        call.setBoolean(14, content.getValue('IsVersionable'))
        call.setString(15, parentid)
        result = call.execute()
        call.close()
        return result == 0

    def countChildTitle(self, userid, parentid, title):
        count = 1
        call = self._getDataSourceCall('countChildTitle')
        call.setString(1, userid)
        call.setString(2, parentid)
        call.setString(3, title)
        result = call.executeQuery()
        if result.next():
            count = result.getLong(1)
        call.close()
        return count






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



# Procedures called by the Replicator
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

    def updateDrive(self, provider, user):
        starttime = parseDateTime()
        separator = ','
        call = self._getDataSourceCall('mergeItem', True)
        call.setString(1, user.Id)
        call.setString(2, separator)
        call.setLong(3, 1)
        rootid = user.RootId
        roots = [rootid]
        rows, items, parents, page, row = self._getDriveContent(call, provider, user, rootid, roots, separator, starttime)
        rows += self._filterParents(call, provider, items, parents, roots, separator, starttime)
        rejected = self._getRejectedItems(provider, parents, items)
        self._closeDataSourceCall()
        endtime = parseDateTime()
        #self._updateUserTimeStamp(user.Id, endtime)
        return rejected, rows, page, row, starttime

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

    def _updateUserTimeStamp(self, userid, timestamp):
        call = self._getDataSourceCall('updateUserTimeStamp')
        call.setTimestamp(1, timestamp)
        call.setString(2, userid)
        call.executeUpdate()
        call.close()

    def getUserTimeStamp(self, userid):
        select = self._getDataSourceCall('getUserTimeStamp')
        select.setString(1, userid)
        result = select.executeQuery()
        if result.next():
            timestamp = result.getTimestamp(1)
        select.close()
        return timestamp

    def getUpdated(self, userid, start, stop):
        items = []
        select = self._getDataSourceCall('getUpdated')
        select.setTimestamp(1, start)
        select.setTimestamp(2, stop)
        select.setString(3, userid)
        result = select.executeQuery()
        while result.next():
            items.append(getKeyMapFromResult(result))
        select.close()
        msg = "Get Updated to Sync: %s, %s" % (items, len(items))
        print(msg)

    def getUpdatedItems(self, userid, start, stop):
        items = []
        select = self._getDataSourceCall('getUpdatedItems')
        select.setTimestamp(1, start)
        select.setTimestamp(2, stop)
        select.setString(3, userid)
        result = select.executeQuery()
        while result.next():
            items.append(getKeyMapFromResult(result))
        select.close()
        msg = "Get UpdatedItems to Sync: %s, %s" % (items, len(items))
        print(msg)

    def getInserted(self, userid, start, stop):
        items = []
        select = self._getDataSourceCall('getInserted')
        select.setTimestamp(1, start)
        select.setString(2, userid)
        result = select.executeQuery()
        while result.next():
            items.append(getKeyMapFromResult(result))
        select.close()
        msg = "Get Inserted to Sync: %s, %s" % (items, len(items))
        print(msg)

    def getInsertedItems(self, userid, start, stop):
        items = []
        select = self._getDataSourceCall('getInsertedItems')
        select.setTimestamp(1, start)
        select.setTimestamp(2, stop)
        select.setString(3, userid)
        result = select.executeQuery()
        while result.next():
            items.append(getKeyMapFromResult(result))
        select.close()
        msg = "Get InsertedItems to Sync: %s, %s" % (items, len(items))
        print(msg)

    def getDeletedItems(self, userid, start, stop):
        items = []
        select = self._getDataSourceCall('getDeletedItems')
        select.setTimestamp(1, start)
        select.setString(2, userid)
        select.setString(3, userid)
        result = select.executeQuery()
        while result.next():
            items.append(getKeyMapFromResult(result))
        select.close()
        msg = "Get DeletedItems to Sync: %s, %s" % (items, len(items))
        print(msg)

# Procedures called internally
    def _setCallItem(self, call, provider, item, id, parents, separator, timestamp):
        call.setString(4, id)
        call.setString(5, provider.getItemTitle(item))
        call.setTimestamp(6, provider.getItemCreated(item, timestamp))
        call.setTimestamp(7, provider.getItemModified(item, timestamp))
        call.setString(8, provider.getItemMediaType(item))
        call.setLong(9, provider.getItemSize(item))
        call.setBoolean(10, provider.getItemTrashed(item))
        call.setBoolean(11, provider.getItemCanAddChild(item))
        call.setBoolean(12, provider.getItemCanRename(item))
        call.setBoolean(13, provider.getItemIsReadOnly(item))
        call.setBoolean(14, provider.getItemIsVersionable(item))
        call.setString(15, separator.join(parents))
        return 1

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
