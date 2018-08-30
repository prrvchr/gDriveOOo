#!
# -*- coding: utf_8 -*-

import uno

from com.sun.star.ucb.ConnectionMode import ONLINE

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
    insert.setString(1, id)
    insert.setString(2, parent)
    insert.execute()
    return insert.getLong(3)

# LibreOffice Column: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
# OpenOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']

def getChildSelect(connection, mode, id, url):
    if mode == ONLINE:
        select = connection.prepareCall('CALL "selectChildOn"(?, ?, ?)')
    else:
        select = connection.prepareCall('CALL "selectChildOff"(?, ?, ?)')
    #select.ResultSetType = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE')
    #select.ResultSetConcurrency = uno.getConstantByName('com.sun.star.sdbc.ResultSetConcurrency.UPDATABLE')
    select.setString(1, id)
    url = url if url.endswith('/') else '%s/' % url
    select.setString(2, url)
    return select
