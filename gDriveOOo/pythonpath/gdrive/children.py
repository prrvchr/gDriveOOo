#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getDbConnection, getMarks, parseDateTime
from .items import executeUpdateInsertItem
from .google import ChildGenerator
from .unotools import getResourceLocation, createService
from .logger import getLogger


def updateChildren(ctx, iteminsert, itemupdate, childdelete, childinsert, scheme, username, id):
    timestamp = parseDateTime()
    return all(_updateChild(item, itemupdate, iteminsert, childdelete, childinsert, timestamp)
               for item in ChildGenerator(ctx, scheme, username, id))

def _updateChild(item, itemupdate, iteminsert, childdelete, childinsert, timestamp):
    return all((executeUpdateInsertItem(itemupdate, iteminsert, item, timestamp),
               _updateParent(childdelete, childinsert, item)))

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

def getChildSelect(ctx, connection, id, url, properties):
    columns = ', '.join(_getChildSelectColumns(ctx, url, properties))
    query = 'SELECT %s FROM "Items" AS "I" JOIN "Children" AS "C" ON "I"."Id" = "C"."Id" WHERE "C"."ParentId" = ?;' % columns
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

def insertParent(insert, id, parent):
    insert.setString(1, id)
    insert.setString(2, parent)
    return insert.executeUpdate()

def _updateParent(delete, insert, item):
    id = item['id']
    return all((_deleteParent(delete, id),
                _insertParent(insert, id, item)))

def _deleteParent(delete, id):
    delete.setString(1, id)
    delete.executeUpdate()
    return 1
    
def _insertParent(insert, id, item):
    if 'parents' in item:
        return all(insertParent(insert, id, parent) for parent in item['parents'])
    return 1
