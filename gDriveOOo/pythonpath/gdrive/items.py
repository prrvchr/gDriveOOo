#!
# -*- coding: utf_8 -*-

from .dbtools import getItemFromResult, SqlArray

import traceback


def needSync(connection):
    call = connection.prepareCall('CALL "needSync"(?, ?)')
    call.setLong(1, 4)
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

def mergeUser(connection, user, item, mode):
    root = None
    merge = connection.prepareCall('CALL "mergeUser"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    merge.setString(1, user['Id'])
    merge.setString(2, user['UserName'])
    merge.setString(3, user['DisplayName'])
    index = _setCallParameters(merge, item['Id'], item, 4)
    merge.setLong(index, mode)
    result = merge.executeQuery()
    if result.next():
        root = getItemFromResult(result)
    merge.close()
    return root

def selectItem(connection, id):
    item = None
    data = ('Name', 'DateCreated', 'DateModified', 'MimeType', 'Size',
            'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable', 'SyncMode')
    select = connection.prepareCall('CALL "selectItem"(?)')
    # selectItem(IN ID VARCHAR(100))
    select.setString(1, id)
    result = select.executeQuery()
    if result.next():
        item = getItemFromResult(result, data)
    select.close()
    return item

def insertItem(connection, userid, item):
    try:
        item = None
        data = ('Name', 'DateCreated', 'DateModified', 'MimeType', 'Size',
                'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable', 'SyncMode')
        insert = connection.prepareCall('CALL "insertItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        insert.setString(1, userid)
        index = _setCallParameters(insert, item['Id'], item['Data'], 2)
        # Never managed to run the next line: Implement me ;-)
        #insert.setArray(index, SqlArray(item['Parents'], 'VARCHAR'))
        result = insert.executeQuery()
        if result.next():
            item = getItemFromResult(result, data)
        insert.close()
        return item
    except Exception as e:
        print("items.insertItem().Error: %s - %s" % (e, traceback.print_exc()))

def mergeItem(merge, userid, item):
    merge.setString(1, userid)
    index = _setCallParameters(merge, item['Id'], item, 2)
    # Never managed to run the next line: Implement me ;-)
    #merge.setArray(index, SqlArray(item['Parents'], 'VARCHAR'))
    merge.execute()
    return merge.getLong(index)

def _setCallParameters(call, id, data, index=1):
    # IN Call Parameters for: mergeUser(), insertItem(), mergeItem()
    # Id, Name, DateCreated, DateModified, MimeType, Size, CanAddChild, CanRename, IsReadOnly, IsVersionable
    # OUT Call Parameters for: mergeItem()
    # RowCount
    call.setString(index, id)
    index += 1
    call.setString(index, data['Name'])
    index += 1
    call.setTimestamp(index, data['DateCreated'])
    index += 1
    call.setTimestamp(index, data['DateModified'])
    index += 1
    call.setString(index, data['MimeType'])
    index += 1
    call.setLong(index, data['Size'])
    index += 1
    call.setBoolean(index, data['CanAddChild'])
    index += 1
    call.setBoolean(index, data['CanRename'])
    index += 1
    call.setBoolean(index, data['IsReadOnly'])
    index += 1
    call.setBoolean(index, data['IsVersionable'])
    index += 1
    return index

