#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getCapabilities, getItemFromResult, parseDateTime, getMarks, getFieldMarks


def selectItem(connection, id):
    retrived, item = False, {}
    call = connection.prepareCall('CALL "getItem"(?)')
    call.setString(1, id)
    result = call.executeQuery()
    if result.next():
        retrived, item = True, getItemFromResult(result)
    call.close()
    print("items.getItem(): %s - %s " % (retrived, item))
    return retrived, item

def insertItem(connection, json):
    retrived, item = False, {}
    call = connection.prepareCall('CALL "insertItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    _setCallParameters(call, json, parseDateTime())
    result = call.executeQuery()
    if result.next():
        retrived, item = True, getItemFromResult(result)
    call.close()
    print("items.insertItem(): %s - %s" % (retrived, item))
    return retrived, item

def mergeItem(call, json, timestamp):
    _setCallParameters(call, json, timestamp)
    call.execute()
    row = call.getLong(11)
    print("users.mergeItem(): %s" % (row, ))
    return row

def _setCallParameters(call, json, timestamp):
    call.setString(1, json['id'])
    call.setString(2, json['name'])
    call.setTimestamp(3, parseDateTime(json['createdTime']) if 'createdTime' in json else timestamp)
    call.setTimestamp(4, parseDateTime(json['modifiedTime']) if 'modifiedTime' in json else timestamp)
    call.setString(5, json['mimeType'])
    call.setBoolean(6, not getCapabilities(json, 'canEdit', True))
    call.setBoolean(7, getCapabilities(json, 'canRename', False))
    call.setBoolean(8, getCapabilities(json, 'canAddChildren', False))
    call.setLong(9, int(json['size']) if 'size' in json else 0)
    call.setBoolean(10, getCapabilities(json, 'canReadRevisions', False))

def _getItemSelectColumns():
    columns = ('"Id"',
               '"Title"',
               '"DateCreated"',
               '"DateModified"',
               '"MediaType"',
               '"IsReadOnly"',
               '"CanRename"',
               '"CanAddChild"',
               '"Size"',
               '"IsVersionable"',
               '"IsRead"')
    return columns
    
def executeUpdateInsertItem(update, insert, json, timestamp=None):
    timestamp = parseDateTime() if timestamp is None else timestamp
    _setUpdateParameters(update, json, timestamp)
    result = update.executeUpdate()
    if not result:
        _setInsertParameters(insert, json, timestamp)
        result = insert.executeUpdate()
    return result

def getItemInsert(connection):
    fields = _getInsertColumns()
    columns = ', '.join(fields)
    marks = ', '.join(getMarks(fields))
    query = 'INSERT INTO "Items" (%s, "TimeStamp") VALUES (%s, CURRENT_TIMESTAMP(3));' % (columns, marks)
    return connection.prepareStatement(query)

def getItemUpdate(connection):
    columns = ', '.join(getFieldMarks(_getUpdateColumns()))
    query = 'UPDATE "Items" SET %s, "TimeStamp" = CURRENT_TIMESTAMP(3) WHERE "Id" = ?;' % columns
    return connection.prepareStatement(query)

def executeItemInsert(insert, json):
    timestamp = parseDateTime()
    _setInsertParameters(insert, json, timestamp)
    return insert.executeUpdate()

def updateItem(event, statement, id):
    query = 'UPDATE "Items" SET "%s" = ?, "TimeStamp" = CURRENT_TIMESTAMP(3) WHERE "Id" = ?;' % event.PropertyName
    update = statement.getConnection().prepareStatement(query)
    update.setString(2, id)
    if event.PropertyName == 'IsRead':
        update.setBoolean(1, event.NewValue)
    elif event.PropertyName == 'IsWrite':
        update.setBoolean(1, event.NewValue)
    elif event.PropertyName == 'Title':
        update.setString(1, event.NewValue)
    elif event.PropertyName == 'Size':
        update.setLong(1, event.NewValue)
    return update.executeUpdate()

def insertItem(insert, id, row):
    insert.setString(1, id)
    insert.setString(2, row.getString(2))
    insert.setTimestamp(3, row.getTimestamp(3))
    insert.setTimestamp(4, row.getTimestamp(4))
    insert.setString(5, row.getString(5))
    insert.setBoolean(6, False)
    insert.setBoolean(7, True)
    insert.setBoolean(8, row.getBoolean(6))
    insert.setLong(9, row.getLong(7))
    insert.setBoolean(10, row.getBoolean(8))
    insert.setBoolean(11, True)
    return insert.executeUpdate()

def _setInsertParameters(insert, json, timestamp, incache=False):
    insert.setString(1, json['id'])
    index = _setInsertUpdateParameters(insert, json, timestamp, 2)
    insert.setBoolean(index, incache)

def _setUpdateParameters(update, json, timestamp):
    index = _setInsertUpdateParameters(update, json, timestamp, 1)
    update.setString(index, json['id'])

def _setInsertUpdateParameters(statement, json, timestamp, index):
    statement.setString(index, json['name'] if 'name' in json else 'sans nom')
    index += 1
    created = parseDateTime(json['createdTime']) if 'createdTime' in json else timestamp
    statement.setTimestamp(index, created)
    index += 1
    modified = parseDateTime(json['modifiedTime']) if 'modifiedTime' in json else timestamp
    statement.setTimestamp(index, modified)
    index += 1
    statement.setString(index, json['mimeType'])
    index += 1
    readonly, canrename, addchild, isversionable = True, False, False, False
    if 'capabilities' in json:
        capabilities = json['capabilities']
        if 'canEdit' in capabilities:
            readonly = not capabilities['canEdit']
        if 'canRename' in capabilities:
            canrename = capabilities['canRename']
        if 'canAddChildren' in capabilities:
            addchild = capabilities['canAddChildren']
        if 'canReadRevisions' in capabilities:
            isversionable = capabilities['canReadRevisions']
    statement.setBoolean(index, readonly)
    index += 1
    statement.setBoolean(index, canrename)
    index += 1
    statement.setBoolean(index, addchild)
    index += 1
    statement.setLong(index, int(json['size']) if 'size' in json else 0)
    index += 1
    statement.setBoolean(index, isversionable)
    index += 1
    return index

def _getInsertColumns():
    columns = ('"Id"',
               '"Title"',
               '"DateCreated"',
               '"DateModified"',
               '"MediaType"',
               '"IsReadOnly"',
               '"CanRename"',
               '"CanAddChild"',
               '"Size"',
               '"IsVersionable"',
               '"IsRead"')
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
               '"IsVersionable"')
    return columns
