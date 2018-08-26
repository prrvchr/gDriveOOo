#!
# -*- coding: utf_8 -*-

import uno

from com.sun.star.ucb.ConnectionMode import ONLINE

from .dbtools import parseDateTime, getMarks
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
    try:
        timestamp = parseDateTime()
        merge = connection.prepareCall('CALL "mergeItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        delete = connection.prepareCall('CALL "deleteChild"(?)')
        insert = connection.prepareCall('CALL "insertChild"(?, ?, ?)')
        result = all(updateChild(merge, delete, insert, item, timestamp) for item in ChildGenerator(ctx, scheme, username, id))
        merge.close()
        delete.close()
        insert.close()
        return result
    except Exception as e:
        print("children.updateChildren().Error: %s - %s" % (e, traceback.print_exc()))

def updateChild(merge, delete, insert, item, timestamp):
    result = all((mergeItem(merge, item, timestamp), updateParent(delete, insert, item)))
    print("children.updateChild() %s" % result)
    return result

# LibreOffice Column: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
# OpenOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
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

def getChildSelect(ctx, connection, mode, id, url, properties):
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

def updateParent(delete, insert, item):
    result = 0
    print("children.updateParent()")
    id = item['id']
    result = all((deleteParent(delete, id), insertParent(insert, id, item)))
    print("children.updateParent() %s" % result)
    return result

def deleteParent(delete, id):
    print("children.deleteParent()")
    delete.setString(1, id)
    delete.execute()
    return 1
    
def insertParent(insert, id, item):
    print("children.insertParent()")
    if 'parents' in item:
        return all(_insertParent(insert, id, parent) for parent in item['parents'])
    return 1

def _insertParent(insert, id, parent):
    print("children._insertParent()")
    insert.setString(1, id)
    insert.setString(2, parent)
    insert.execute()
    result = insert.getLong(3)
    print("children._insertParent() %s" % result)
    return result