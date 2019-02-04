#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getItemFromResult, SqlArray
from .google import parseDateTime, unparseDateTime
from .google import ACQUIRED, CREATED, RENAMED, REWRITED, TRASHED

import traceback


def needSync(connection):
    call = connection.prepareCall('CALL "needSync"(?, ?)')
    call.setLong(1, ACQUIRED)
    call.execute()
    sync = call.getBoolean(2)
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

def selectItem(connection, id):
    item = None
    data = ('Name', 'DateCreated', 'DateModified', 'MimeType', 'Size', 'Trashed',
            'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable', 'Loaded')
    select = connection.prepareCall('CALL "selectItem"(?)')
    # selectItem(IN ID VARCHAR(100))
    select.setString(1, id)
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

def insertJsonItem(connection, identifier, data):
    item = None
    fields = ('Name', 'DateCreated', 'DateModified', 'MimeType', 'Size', 'Trashed',
              'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable', 'Loaded')
    insert = connection.prepareCall('CALL "insertJsonItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    insert.setString(1, identifier.User.Id)
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

def insertContentItemCall(connection):
    # (IN USERID VARCHAR(100),IN ITEMID VARCHAR(100),IN PARENTSID VARCHAR(1000),IN SYNC SMALLINT,IN NAME VARCHAR(100),IN DATECREATED TIMESTAMP(3),IN DATEMODIFIED TIMESTAMP(3),IN MEDIATYPE VARCHAR(100),IN SIZE BIGINT,IN TRASHED BOOLEAN,IN CANADDCHILD BOOLEAN,IN CANRENAME BOOLEAN,IN ISREADONLY BOOLEAN,IN ISVERSIONABLE BOOLEAN,IN LOADED SMALLINT,OUT ROWCOUNT SMALLINT)
    return connection.prepareCall('CALL "insertContentItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')

def insertContentItem(insert, row, properties, index=1):
    index = _setContentData(insert, row, properties, index)
    # Never managed to run the next line: Implement me ;-)
    #merge.setArray(index, SqlArray(item['Parents'], 'VARCHAR'))
    insert.execute()
    return insert.getLong(index)

def _setJsonData(call, data, timestamp, index=1):
    # IN Call Parameters for: mergeJsonUser(), insertJsonItem(), mergeJsonItem()
    # Id, Name, DateCreated, DateModified, MimeType, Size, CanAddChild, CanRename, IsReadOnly, IsVersionable, SyncMode, ParentsId
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

def _setContentData(call, row, properties, index=1):
    for i, name in enumerate(properties, start=1):
        value = row.getObject(i, None)
        print ("items._setContentData(): name:%s - value:%s" % (name, value))
        if value is None:
            continue
        if name in ('Name', 'MimeType'):
            call.setString(index, value)
        elif name in ('DateCreated', 'DateModified'):
            call.setTimestamp(index, value)
        elif name in ('Trashed', 'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable'):
            call.setBoolean(index, value)
        elif name in ('Size', 'Loaded', 'SyncMode'):
            call.setLong(index, value)
        index += 1
    return index
