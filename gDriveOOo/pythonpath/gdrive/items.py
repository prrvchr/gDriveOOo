#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getMarks, getFieldMarks, parseDateTime


def _getItemSelectColumns():
    columns = ('"I"."Id" "Id"',
               '"I"."Title" "Title"',
               '"I"."DateCreated" "DateCreated"',
               '"I"."DateModified" "DateModified"',
               '"I"."MediaType" "MediaType"',
               '"I"."IsReadOnly" "IsReadOnly"',
               '"I"."CanRename" "CanRename"',
               '"I"."CanAddChild" "CanAddChild"',
               '"I"."Size" "Size"',
               '"I"."IsInCache" "IsInCache"',
               '"C"."ParentId" "ParentId"')
    return columns

def getItemSelect(connection, id):
    columns = ', '.join(_getItemSelectColumns())
    query = 'SELECT %s FROM "Items" AS "I" LEFT JOIN "Children" AS "C" ON "I"."Id" = "C"."Id" WHERE "I"."Id" = ?' % columns
    select = connection.prepareStatement(query)
    select.setString(1, id)
    return select
    
def executeUpdateInsertItem(connection, item):
    update = getItemUpdate(connection)
    insert = getItemInsert(connection)
    return doUpdateInsertItem(insert, update, item)

def getItemInsert(connection):
    fields = _getInsertColumns()
    columns = ', '.join(fields)
    marks = ', '.join(getMarks(fields))
    query = 'INSERT INTO "Items" (%s, "TimeStamp") VALUES (%s, NOW())' % (columns, marks)
    return connection.prepareStatement(query)

def getItemUpdate(connection, query=None):
    if query is None:
        columns = ', '.join(getFieldMarks(_getUpdateColumns()))
        query = 'UPDATE "Items" SET %s, "TimeStamp" = NOW() WHERE "Id" = ?' % columns
    return connection.prepareStatement(query)

def doUpdateInsertItem(insert, update, item, incache=False, timestamp=None):
    timestamp = parseDateTime() if timestamp is None else timestamp
    _setItemUpdateParameters(update, item, incache, timestamp)
    result = update.executeUpdate()
    if not result:
        _setItemInsertParameters(insert, item, timestamp)
        result = insert.executeUpdate()
    print("items.doUpdateInsertItem() %s" % result)
    return result

def executeItemInsert(connection, item):
    timestamp = parseDateTime()
    insert = getItemInsert(connection)
    _setItemInsertParameters(insert, item, timestamp)
    return insert.executeUpdate()

def updateItem(connection, id, name, value):
    updated = 0
    query = 'UPDATE "Items" SET "%s" = ?, "TimeStamp" = NOW() WHERE "Id" = ?' % name
    update = getItemUpdate(connection, query)
    update.setString(2, id)
    if name == 'IsInCache':
        update.setBoolean(1, value)
    elif name == 'Title':
        update.setString(1, value)
    elif name == 'Size':
        update.setLong(1, value)
    return update.executeUpdate()

def _setItemInsertParameters(statement, item, timestamp):
    statement.setString(1, item['id'])
    _setItemInsertUpdateParameters(statement, item, timestamp, 2)

def _setItemUpdateParameters(statement, item, incache, timestamp):
    _setItemInsertUpdateParameters(statement, item, timestamp, 1)
    statement.setBoolean(9, incache)
    statement.setBoolean(10, True)
    statement.setString(11, item['id'])

def _setItemInsertUpdateParameters(statement, item, timestamp, index):
    statement.setString(index, item['name'] if 'name' in item else 'sans nom')
    created = parseDateTime(item['createdTime']) if 'createdTime' in item else timestamp
    statement.setTimestamp(index +1, created)
    modified = parseDateTime(item['modifiedTime']) if 'modifiedTime' in item else timestamp
    statement.setTimestamp(index +2, modified)
    statement.setString(index +3, item['mimeType'])
    readonly, canrename, addchild = True, False, False
    if 'capabilities' in item:
        capabilities = item['capabilities']
        if 'canEdit' in capabilities:
            readonly = not capabilities['canEdit']
        if 'canRename' in capabilities:
            canrename = capabilities['canRename']
        if 'canAddChildren' in capabilities:
            addchild = capabilities['canAddChildren']
    statement.setBoolean(index +4, readonly)
    statement.setBoolean(index +5, canrename)
    statement.setBoolean(index +6, addchild)
    statement.setDouble(index +7, item['size'] if 'size' in item else 0)

def _getInsertColumns():
    columns = ('"Id"',
               '"Title"',
               '"DateCreated"',
               '"DateModified"',
               '"MediaType"',
               '"IsReadOnly"',
               '"CanRename"',
               '"CanAddChild"',
               '"Size"')
    return columns

def _getUpdateColumns():
    columns = ('"Title"',
               '"DateCreated"',
               '"DateModified"', 
               '"MediaType"', 
               '"IsReadOnly"', 
               '"CanRename"', 
               '"CanAddChild"', 
               '"Size"', 
               '"IsInCache"', 
               '"Updated"')
    return columns
