#!
# -*- coding: utf_8 -*-

from .dbtools import getItemFromResult, SqlArray

import traceback


def selectUser(connection, username):
    select = connection.prepareCall('CALL "selectUser"(?)')
    # selectUser(IN USERNAME VARCHAR(100))
    select.setString(1, username)
    result = select.executeQuery()
    retrived, root = False, {}
    if result.next():
        retrived, root = True, getItemFromResult(result)
    select.close()
    return retrived, root

def mergeUser(connection, user, item):
    merge = connection.prepareCall('CALL "mergeUser"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    merge.setString(1, user['Id'])
    merge.setString(2, user['UserName'])
    merge.setString(3, user['DisplayName'])
    dummy = _setCallParameters(merge, item, 4)
    result = merge.executeQuery()
    retrived, root = False, {}
    if result.next():
        retrived, root = True, getItemFromResult(result)
    merge.close()
    return retrived, root

def selectItem(connection, userid, itemid):
    select = connection.prepareCall('CALL "selectItem"(?, ?)')
    # selectItem(IN ID VARCHAR(100))
    select.setString(1, userid)
    select.setString(2, itemid)
    result = select.executeQuery()
    retrived, item = False, {}
    if result.next():
        retrived, item = True, getItemFromResult(result)
    select.close()
    return retrived, item

def insertItem(connection, userid, item):
    try:
        insert = connection.prepareCall('CALL "insertItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        insert.setString(1, userid)
        index = _setCallParameters(insert, item, 2)
        # Never managed to run the next line: Implement me ;-)
        #insert.setArray(index, SqlArray(item['Parents'], 'VARCHAR'))
        result = insert.executeQuery()
        retrived, item = False, {}
        if result.next():
            retrived, item = True, getItemFromResult(result)
        insert.close()
        return retrived, item
    except Exception as e:
        print("items.insertItem().Error: %s - %s" % (e, traceback.print_exc()))

def mergeItem(merge, userid, item):
    merge.setString(1, userid)
    index = _setCallParameters(merge, item, 2)
    # Never managed to run the next line: Implement me ;-)
    #merge.setArray(index, SqlArray(item['Parents'], 'VARCHAR'))
    merge.execute()
    return merge.getLong(index)

def _setCallParameters(call, item, index=1):
    # IN Call Parameters for: mergeUser(), insertItem(), mergeItem()
    # Id, Title, DateCreated, DateModified, MediaType, Size, CanAddChild, CanRename, IsReadOnly, IsVersionable
    # OUT Call Parameters for: mergeItem()
    # RowCount
    call.setString(index, item['Id'])
    index += 1
    call.setString(index, item['Name'])
    index += 1
    call.setTimestamp(index, item['DateCreated'])
    index += 1
    call.setTimestamp(index, item['DateModified'])
    index += 1
    call.setString(index, item['MediaType'])
    index += 1
    call.setLong(index, item['Size'])
    index += 1
    call.setBoolean(index, item['CanAddChild'])
    index += 1
    call.setBoolean(index, item['CanRename'])
    index += 1
    call.setBoolean(index, item['IsReadOnly'])
    index += 1
    call.setBoolean(index, item['IsVersionable'])
    index += 1
    return index

