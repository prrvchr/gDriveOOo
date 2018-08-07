#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getDbConnection, getMarks, parseDateTime
from .items import getItemInsert, getItemUpdate, doUpdateInsertItem
from .google import ChildGenerator
from .unotools import getResourceLocation, createService
from .logger import getLogger


def updateChildren(ctx, connection, scheme, username, id):
    timestamp = parseDateTime()
    iteminsert = getItemInsert(connection)
    itemupdate = getItemUpdate(connection)
    childdelete = _getChildDelete(connection)
    childinsert = _getChildInsert(connection)
    for item in ChildGenerator(ctx, scheme, username, id):
        doUpdateInsertItem(iteminsert, itemupdate, item, False, timestamp)
        _updateParent(childdelete, childinsert, item, timestamp)
    print("children.updateChildren() 1")


# LibreOffice Column: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
# OpenOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
def _getChildSelectColumns(username, properties):
    columns = []
    fields = {}
    fields['Title'] = '"I"."Title"'
    fields['Size'] = '"I"."Size"'
    fields['DateModified'] = '"I"."DateModified"'
    fields['DateCreated'] = '"I"."DateCreated"'
    fields['IsFolder'] = '"I"."CanAddChild"'
    fields['TargetURL'] = 'CONCAT(\'vnd.google-apps://%s/\', "I"."Id")' % username
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
            getLogger().logp(level, "children", "_getChildSelectColumns()", "Column not found: %s... ERROR" % property.Name)
    return columns

def getChildSelect(connection, username, id, properties):
    columns = ', '.join(_getChildSelectColumns(username, properties))
    query = 'SELECT %s FROM "Items" AS "I" JOIN "Children" AS "C" ON "I"."Id" = "C"."Id" WHERE "C"."ParentId" = ?' % columns
    select = connection.prepareStatement(query)
    select.ResultSetType = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_SENSITIVE')
    #select.ResultSetConcurrency = uno.getConstantByName('com.sun.star.sdbc.ResultSetConcurrency.UPDATABLE')
    select.setString(1, id)
    return select

def _getChildDelete(connection):
    query = 'DELETE FROM "Children" WHERE "Id" = ?'
    return connection.prepareStatement(query)

def _getChildInsert(connection):
    query = _getInsertQuery()
    return connection.prepareStatement(query)

def insertParent(connection, arguments):
    query = _getInsertQuery()
    insert = connection.prepareStatement(query)
    insert.setString(1, arguments['Id'])
    insert.setString(2, arguments['ParentId'])
    return insert.executeUpdate()

def _getInsertQuery():
    query = 'INSERT INTO "Children" ("Id", "ParentId", "TimeStamp") VALUES (?, ?, NOW())'
    return query

def _updateParent(delete, insert, result, timestamp):
    id = result['id']
    delete.setString(1, id)
    delete.executeUpdate()
    if 'parents' in result:
        for parent in result['parents']:
            insert.setString(1, id)
            insert.setString(2, parent)
            insert.executeUpdate()
