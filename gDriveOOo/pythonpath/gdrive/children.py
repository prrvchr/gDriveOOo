#!
# -*- coding: utf_8 -*-

import uno

from com.sun.star.ucb.ConnectionMode import OFFLINE

from .items import mergeItem
from .google import ChildGenerator


def isChild(connection, id, parent):
    ischild = False
    call = connection.prepareCall('CALL "isChild"(?, ?)')
    call.setString(1, id)
    call.setString(2, parent)
    result = call.executeQuery()
    if result.next():
        ischild = result.getBoolean(1)
    call.close()
    return ischild

def updateChildren(ctx, connection, scheme, username, id):
    merge = connection.prepareCall('CALL "mergeItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    insert = connection.prepareCall('CALL "insertChild"(?, ?, ?)')
    result = all(updateChild(merge, insert, item) for item in ChildGenerator(ctx, scheme, username, id))
    merge.close()
    insert.close()
    return result

def updateChild(merge, insert, item):
    return all((mergeItem(merge, item), updateParent(insert, item)))

def updateParent(insert, item):
    result = True
    if 'Parents' in item:
        id = item['Id']
        result = all(insertParent(insert, id, parent) for parent in item['Parents'])
    return result

def insertParent(insert, id, parent):
    # insertChild(IN ID VARCHAR(100),IN PARENT VARCHAR(100),OUT ROWCOUNT SMALLINT)
    insert.setString(1, id)
    insert.setString(2, parent)
    insert.execute()
    return insert.getLong(3)

def getChildSelect(connection, mode, id, uri, isroot):
    # LibreOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
    # OpenOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
    index, select = 1, connection.prepareCall('CALL "selectChild"(?, ?, ?, ?)')
    # Never managed to run the next line: select return RowCount as OUT parameter in select.getLong(index)!!!
    #select.ResultSetType = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE')
    # selectChild(IN ID VARCHAR(100),IN URL VARCHAR(250),IN OFFLINE BOOLEAN,OUT ROWCOUNT SMALLINT)
    select.setString(index, id)
    index += 1
    # "TargetURL" is done by CONCAT(uri,id)... The root uri already ends with a '/' ...
    select.setString(index, uri if isroot else '%s/' % uri)
    index += 1
    select.setBoolean(index, mode == OFFLINE)
    index += 1
    return index, select
