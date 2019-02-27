#!
# -*- coding: utf_8 -*-

import uno

from .contenttools import setContentData
from .dbtools import getItemFromResult
from .dbtools import SqlArray
from .google import parseDateTime
from .google import unparseDateTime
from .google import RETRIEVED
from .google import RENAMED
from .google import REWRITED
from .google import TRASHED


def needSync(connection, id):
    call = connection.prepareCall('CALL "needSync"(?, ?, ?)')
    call.setString(1, id)
    call.setLong(2, RETRIEVED)
    call.execute()
    sync = call.getBoolean(3)
    call.close()
    return sync

def selectUser(connection, username, mode):
    user, select = None, connection.prepareCall('CALL "selectUser"(?, ?)')
    # selectUser(IN USERNAME VARCHAR(100),IN MODE SMALLINT)
    select.setString(1, username)
    select.setLong(2, mode)
    result = select.executeQuery()
    if result.next():
        user = getItemFromResult(result)
    select.close()
    return user

def selectItem(connection, userid, id):
    item = None
    data = ('Name', 'DateCreated', 'DateModified', 'MimeType', 'Size', 'Trashed',
            'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable', 'Loaded')
    select = connection.prepareCall('CALL "selectItem"(?, ?)')
    # selectItem(IN USERID VARCHAR(100),IN ID VARCHAR(100))
    select.setString(1, userid)
    select.setString(2, id)
    result = select.executeQuery()
    if result.next():
        item = getItemFromResult(result, data)
    select.close()
    return item

def mergeJsonUser(connection, user, data, mode):
    root = None
    merge = connection.prepareCall('CALL "mergeJsonUser"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    merge.setString(1, user.get('permissionId'))
    merge.setString(2, user.get('emailAddress'))
    merge.setString(3, user.get('displayName'))
    index = _setJsonData(merge, data, unparseDateTime(), 4)
    merge.setLong(index, mode)
    #ctx = uno.getComponentContext()
    #mri = ctx.ServiceManager.createInstance('mytools.Mri')
    #mri.inspect(merge1)
    result = merge.executeQuery()
    if result.next():
        root = getItemFromResult(result)
    merge.close()
    return root

def insertJsonItem(connection, userid, data):
    item = None
    fields = ('Name', 'DateCreated', 'DateModified', 'MimeType', 'Size', 'Trashed',
              'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable', 'Loaded')
    insert = connection.prepareCall('CALL "insertJsonItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    insert.setString(1, userid)
    index = _setJsonData(insert, data, unparseDateTime(), 2)
    parents = ','.join(data.get('parents', ()))
    insert.setString(index, parents)
    # Never managed to run the next line: Implement me ;-)
    #insert.setArray(index, SqlArray(item['Parents'], 'VARCHAR'))
    result = insert.executeQuery()
    if result.next():
        item = getItemFromResult(result, fields)
    insert.close()
    return item

def mergeJsonItemCall(connection, userid):
    merge = connection.prepareCall('CALL "mergeJsonItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    merge.setString(1, userid)
    return merge, 2

def mergeJsonItem(merge, data, index=1):
    index = _setJsonData(merge, data, unparseDateTime(), index)
    parents = ','.join(data.get('parents', ()))
    merge.setString(index, parents)
    # Never managed to run the next line: Implement me ;-)
    #merge.setArray(index, SqlArray(item['Parents'], 'VARCHAR'))
    merge.execute()
    return merge.getLong(index +1)

def insertContentItem(content, identifier, value):
    properties = ('Name', 'DateCreated', 'DateModified', 'MimeType', 'Size', 'Trashed',
                  'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable', 'Loaded')
    insert = identifier.User.Connection.prepareCall('CALL "insertContentItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    insert.setString(1, identifier.User.Id)
    insert.setString(2, identifier.Id)
    insert.setString(3, identifier.getParent().Id)
    insert.setString(4, value)
    result = _insertContentItem(content, insert, properties, 5)
    insert.close()
    return result

def updateName(identifier, value):
    update = identifier.User.Connection.prepareCall('CALL "updateName"(?, ?, ?, ?, ?)')
    update.setString(1, identifier.User.Id)
    update.setString(2, identifier.Id)
    update.setString(3, value)
    update.setLong(4, RENAMED)
    update.execute()
    result = update.getLong(5)
    update.close()
    return result

def updateSize(identifier, value):
    update = identifier.User.Connection.prepareCall('CALL "updateSize"(?, ?, ?, ?, ?)')
    update.setString(1, identifier.User.Id)
    update.setString(2, identifier.Id)
    update.setLong(3, value)
    update.setLong(4, REWRITED)
    update.execute()
    result = update.getLong(5)
    update.close()
    return result

def updateTrashed(identifier, value):
    update = identifier.User.Connection.prepareCall('CALL "updateTrashed"(?, ?, ?, ?, ?)')
    update.setString(1, identifier.User.Id)
    update.setString(2, identifier.Id)
    update.setLong(3, value)
    update.setLong(4, TRASHED)
    update.execute()
    result = update.getLong(5)
    update.close()
    return result

def updateLoaded(identifier, value):
    update = identifier.User.Connection.prepareCall('CALL "updateLoaded"(?, ?, ?, ?)')
    update.setString(1, identifier.User.Id)
    update.setString(2, identifier.Id)
    update.setLong(3, value)
    update.execute()
    result = update.getLong(4)
    update.close()
    return result

def _insertContentItem(content, insert, properties, index=1):
    index = setContentData(content, insert, properties, index)
    # Never managed to run the next line: Implement me ;-)
    #merge.setArray(index, SqlArray(item['Parents'], 'VARCHAR'))
    insert.execute()
    return insert.getLong(index)

def _setJsonData(call, data, timestamp, index=1):
    # IN Call Parameters for: mergeJsonUser(), insertJsonItem(), mergeJsonItem()
    # Id, Name, DateCreated, DateModified, MimeType, Size, CanAddChild, CanRename, IsReadOnly, IsVersionable, ParentsId
    # OUT Call Parameters for: mergeJsonItem()
    # RowCount
    call.setString(index, data.get('id'))
    index += 1
    call.setString(index, data.get('name'))
    index += 1
    call.setTimestamp(index, parseDateTime(data.get('createdTime', timestamp)))
    index += 1
    call.setTimestamp(index, parseDateTime(data.get('modifiedTime', timestamp)))
    index += 1
    call.setString(index, data.get('mimeType', 'application/octet-stream'))
    index += 1
    call.setLong(index, int(data.get('size', 0)))
    index += 1
    call.setBoolean(index, data.get('trashed', False))
    index += 1
    call.setBoolean(index, data.get('capabilities', {}).get('canAddChildren', False))
    index += 1
    call.setBoolean(index, data.get('capabilities', {}).get('canRename', False))
    index += 1
    call.setBoolean(index, not data.get('capabilities', {}).get('canEdit', False))
    index += 1
    call.setBoolean(index, data.get('capabilities', {}).get('canReadRevisions', False))
    index += 1
    return index
