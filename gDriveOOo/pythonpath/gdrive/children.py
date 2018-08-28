#!
# -*- coding: utf_8 -*-

import uno

from com.sun.star.ucb.ConnectionMode import ONLINE

from .dbtools import getMarks
from .items import mergeItem, executeUpdateInsertItem
from .google import ChildGenerator
from .unotools import getResourceLocation, createService
from .logger import getLogger

import traceback


def isChildOfItem(connection, id, parent):
    ischild = False
    call = connection.prepareCall('CALL "isChildOfItem"(?, ?)')
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

def _getChildSelectColumns(ctx, url, properties):
    if not url.endswith('/'):
        url += '/'
    columns = []
    fields = {}
    fields['Title'] = '"I"."Title"'
    fields['Size'] = '"I"."Size"'
    fields['DateModified'] = '"I"."DateModified"'
    fields['DateCreated'] = '"I"."DateCreated"'
    fields['IsFolder'] = '"I"."CanAddChild"'
    fields['TargetURL'] = 'CONCAT(\'%s\', "I"."Id")' % url
    fields['IsHidden'] = 'FALSE'
    fields['IsVolume'] = 'FALSE'
    fields['IsRemote'] = 'FALSE'
    fields['IsRemoveable'] = 'FALSE'
    fields['IsFloppy'] = 'FALSE'
    fields['IsCompactDisc'] = 'FALSE'
    for property in properties:
        if hasattr(property, 'Name') and property.Name in fields:
            columns.append('%s "%s"' % (fields[property.Name], property.Name))
        else:
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
            getLogger(ctx).logp(level, "children", "_getChildSelectColumns()", "Column not found: %s... ERROR" % property.Name)
    return columns

def getChildSelect1(ctx, connection, mode, id, url, properties):
    columns = ', '.join(_getChildSelectColumns(ctx, url, properties))
    filter = '' if mode == ONLINE else ' AND "I"."IsRead" = TRUE'
    query = 'SELECT %s FROM "Items" AS "I" JOIN "Children" AS "C" ON "I"."Id" = "C"."Id" WHERE "C"."ParentId" = ?%s;' % (columns, filter)
    select = connection.prepareStatement(query)
    select.ResultSetType = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_SENSITIVE')
    #select.ResultSetConcurrency = uno.getConstantByName('com.sun.star.sdbc.ResultSetConcurrency.UPDATABLE')
    select.setString(1, id)
    return select

def getChildDelete(connection):
    query = 'DELETE FROM "Children" WHERE "Id" = ?;'
    return connection.prepareStatement(query)

def getChildInsert(connection):
    query = 'INSERT INTO "Children" ("Id", "ParentId", "TimeStamp") VALUES (?, ?, CURRENT_TIMESTAMP(3) );'
    return connection.prepareStatement(query)
