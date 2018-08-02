#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getMarks, getFieldMarks, parseDateTime

g_folder = 'application/vnd.google-apps.folder'


def getItemInsert(connection):
    query = _getInsertQuery()
    insert = connection.prepareStatement(query)
    return insert

def getItemUpdate(connection, query=None):
    if query is None:
        query = _getUpdateQuery()
    update = connection.prepareStatement(query)
    return update

def executeItemUpdate(insert, update, result, incache=False, timestamp=None):
    timestamp = parseDateTime() if timestamp is None else timestamp
    _setItemUpdateParameters(update, result, incache, timestamp)
    if not update.executeUpdate():
        _setItemInsertParameters(insert, result, timestamp)
        insert.executeUpdate()

def executeItemInsert(statement, result):
    timestamp = parseDateTime()
    _setItemInsertParameters(statement, result, False, timestamp)
    return statement.executeUpdate()

def insertItem(insert, arguments):
    _setInsertArguments(insert, arguments)
    insert.executeUpdate()

def updateItem(update, arguments, updated=False):
    _setUpdatedArguments(update, arguments, updated)
    return update.executeUpdate()

def _getUpdatedArguments(select, id, update={}):
    select.setString(2, id)
    result = select.executeQuery()
    result.next()
    columns = result.getColumns()
    arguments = {}
    arguments['Id'] = columns.getByName('Id').getString()
    arguments['Title'] = columns.getByName('Title').getString()
    arguments['DateCreated'] = columns.getByName('DateCreated').getTimestamp()
    arguments['DateModified'] = columns.getByName('DateModified').getTimestamp()
    arguments['MediaType'] = columns.getByName('MediaType').getString()
    arguments['IsReadOnly'] = columns.getByName('IsReadOnly').getBoolean()
    arguments['CanRename'] = columns.getByName('CanRename').getBoolean()
    arguments['CanAddChild'] = columns.getByName('CanAddChild').getBoolean()
    arguments['Size'] = columns.getByName('Size').getDouble()
    arguments['TimeStamp'] = columns.getByName('TimeStamp').getTimestamp()
    arguments['IsInCache'] = columns.getByName('IsInCache').getBoolean()
    arguments['Updated'] = columns.getByName('Updated').getBoolean()
    arguments.update(update)
    return arguments

def _setUpdatedArguments(statement, arguments, updated):
    statement.setString(1, arguments['Title'])
    statement.setTimestamp(2, arguments['DateCreated'])
    statement.setTimestamp(3, arguments['DateModified'])
    statement.setString(4, arguments['MediaType'])
    statement.setBoolean(5, arguments['IsReadOnly'])
    statement.setBoolean(6, arguments['CanRename'])
    statement.setBoolean(7, arguments['CanAddChild'])
    statement.setDouble(8, arguments['Size'])
    statement.setBoolean(9, arguments['IsInCache'])
    statement.setBoolean(10, updated)
    statement.setString(11, arguments['Id'])

def _setInsertArguments(statement, arguments):
    timestamp = parseDateTime()
    statement.setString(1, arguments['Id'])
    statement.setString(2, arguments['Title'])
    statement.setTimestamp(3, timestamp)
    statement.setTimestamp(4, timestamp)
    statement.setString(5, arguments['MediaType'])
    statement.setBoolean(6, False)
    statement.setBoolean(7, True)
    statement.setBoolean(8, True)
    statement.setDouble(9, 0)

def _setItemInsertParameters(statement, result, timestamp):
    statement.setString(1, result['id'])
    _setItemInsertUpdateParameters(statement, result, timestamp, 2)

def _setItemUpdateParameters(statement, result, incache, timestamp):
    _setItemInsertUpdateParameters(statement, result, timestamp, 1)
    statement.setBoolean(9, incache)
    statement.setBoolean(10, True)
    statement.setString(11, result['id'])

def _setItemInsertUpdateParameters(statement, result, timestamp, index):
    statement.setString(index, result['name'] if 'name' in result else 'sans nom')
    created = parseDateTime(result['createdTime']) if 'createdTime' in result else timestamp
    statement.setTimestamp(index +1, created)
    modified = parseDateTime(result['modifiedTime']) if 'modifiedTime' in result else timestamp
    statement.setTimestamp(index +2, modified)
    statement.setString(index +3, result['mimeType'])
    readonly, canrename, addchild = True, False, False
    if 'capabilities' in result:
        capabilities = result['capabilities']
        if 'canEdit' in capabilities:
            readonly = not capabilities['canEdit']
        if 'canRename' in capabilities:
            canrename = capabilities['canRename']
        if 'canAddChildren' in capabilities:
            addchild = capabilities['canAddChildren']
    statement.setBoolean(index +4, readonly)
    statement.setBoolean(index +5, canrename)
    statement.setBoolean(index +6, addchild)
    statement.setDouble(index +7, result['size'] if 'size' in result else 0)

def _getInsertQueryFields():
    fields = []
    fields.append('"Id"')
    fields.append('"Title"')
    fields.append('"DateCreated"')
    fields.append('"DateModified"')
    fields.append('"MediaType"')
    fields.append('"IsReadOnly"')
    fields.append('"CanRename"')
    fields.append('"CanAddChild"')
    fields.append('"Size"')
    return fields

def _getUpdateQueryFields():
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

def _getInsertQuery():
    fields = _getInsertQueryFields()
    marks = getMarks(fields)
    query = 'INSERT INTO "Item" (%s, "TimeStamp") VALUES (%s, NOW())' % (', '.join(fields), ', '.join(marks))
    return query

def _getUpdateQuery():
    fields = _getUpdateQueryFields()
    fieldmarks = getFieldMarks(fields)
    query = 'UPDATE "Item" SET %s, "TimeStamp" = NOW() WHERE "Id" = ?' % ', '.join(fieldmarks)
    return query
