#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getMarks, getFieldMarks, parseDateTime

g_folder = 'application/vnd.google-apps.folder'


def updateItem(update, select, id, arguments):
    _setUpdatedArguments(update, _getUpdatedArguments(select, id, arguments))
    return update.executeUpdate()

def _getUpdatedArguments(select, id, update={}):
    select.setString(2, id)
    result = select.executeQuery()
    result.next()
    columns = result.getColumns()
    arguments = {}
    arguments['FileId'] = columns.getByName('FileId').getString()
    arguments['IsFolder'] = columns.getByName('IsFolder').getBoolean()
    arguments['Title'] = columns.getByName('Title').getString()
    arguments['DateCreated'] = columns.getByName('DateCreated').getTimestamp()
    arguments['DateModified'] = columns.getByName('DateModified').getTimestamp()
    arguments['ContentType'] = columns.getByName('ContentType').getString()
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

def _setUpdatedArguments(statement, arguments):
    statement.setBoolean(1, arguments['IsFolder'])
    statement.setString(2, arguments['Title'])
    statement.setTimestamp(3, arguments['DateCreated'])
    statement.setTimestamp(4, arguments['DateModified'])
    statement.setString(5, arguments['ContentType'])
    statement.setString(6, arguments['MediaType'])
    statement.setBoolean(7, arguments['IsReadOnly'])
    statement.setBoolean(8, arguments['CanRename'])
    statement.setBoolean(9, arguments['CanAddChild'])
    statement.setDouble(10, arguments['Size'])
    statement.setTimestamp(11, arguments['TimeStamp'])
    statement.setBoolean(12, arguments['IsInCache'])
    statement.setBoolean(13, arguments['Updated'])
    statement.setString(14, arguments['FileId'])

def getItemInsertStatement(connection):
    query = _getInsertQuery()
    insert = connection.prepareStatement(query)
    return insert

def getItemSelectStatement(connection, scheme, username=None, id=None):
    query = _getSelectQuery(scheme)
    select = connection.prepareStatement(query)
    scroll = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_SENSITIVE')
    select.ResultSetType = scroll
    concurrency = uno.getConstantByName('com.sun.star.sdbc.ResultSetConcurrency.UPDATABLE')
    select.ResultSetConcurrency = concurrency
    if username is not None:
        select.setString(1, username)
    if id is not None:
        select.setString(2, id)
    return select

def getItemUpdateStatement(connection, id=None):
    query = _getUpdateQuery()
    update = connection.prepareStatement(query)
    if id is not None:
        update.setString(1, id)
    return update

def executeItemUpdateStatement(insert, update, result, incache, timestamp=None):
    _setItemUpdateParameters(update, result, incache, timestamp)
    if not update.executeUpdate():
        _setItemInsertParameters(insert, result, incache, timestamp)
        insert.executeUpdate()

def executeItemInsertStatement(statement, result):
    timestamp = parseDateTime()
    _setItemInsertParameters(statement, result, False, timestamp)
    return statement.executeUpdate()

def _setItemInsertParameters(statement, result, incache, timestamp):
    statement.setString(1, result['id'])
    _setItemInsertUpdateParameters(statement, result, incache, timestamp, 2)

def _setItemUpdateParameters(statement, result, incache, timestamp):
    _setItemInsertUpdateParameters(statement, result, incache, timestamp, 1)
    statement.setString(13, result['id'])

def _setItemInsertUpdateParameters(statement, result, incache, timestamp, index):
    isfolder = False if 'mimeType' in result and result['mimeType'] != g_folder else True
    statement.setBoolean(index, isfolder)
    statement.setString(index +1, result['name'] if 'name' in result else 'sans nom')
    created = parseDateTime(result['createdTime']) if 'createdTime' in result else timestamp
    statement.setTimestamp(index +2, created)
    modified = parseDateTime(result['modifiedTime']) if 'modifiedTime' in result else timestamp
    statement.setTimestamp(index +3, modified)
    mime, content = _getContentType(result)
    statement.setString(index +4, content)
    statement.setString(index +5, mime)
    readonly, canrename, addchild = True, False, False
    if 'capabilities' in result:
        capabilities = result['capabilities']
        if 'canEdit' in capabilities:
            readonly = not capabilities['canEdit']
        if 'canRename' in capabilities:
            canrename = capabilities['canRename']
        if 'canAddChildren' in capabilities:
            addchild = capabilities['canAddChildren']
    statement.setBoolean(index +6, readonly)
    statement.setBoolean(index +7, canrename)
    statement.setBoolean(index +8, addchild)
    statement.setDouble(index +9, result['size'] if 'size' in result else 0)
    statement.setTimestamp(index +10, timestamp)
    statement.setBoolean(index +11, incache)
    
def _getSelectQueryFields(scheme):
    fields = []
    fields.append('\'%s\' AS "Scheme"' % scheme)
    fields.append('U."UserName" AS "UserName"')
    fields.append('I."FileId" AS "FileId"')
    fields.append('I."IsFolder" AS "IsFolder"')
    fields.append('NOT I."IsFolder" AS "IsDocument"')
    fields.append('P."ParentId" AS "ParentId"')
    fields.append('I."Title" AS "Title"')
    fields.append('I."DateCreated" AS "DateCreated"')
    fields.append('I."DateModified" AS "DateModified"')
    fields.append('I."ContentType" AS "ContentType"')
    fields.append('I."MediaType" AS "MediaType"')
    fields.append('I."IsReadOnly" AS "IsReadOnly"')
    fields.append('I."CanRename" AS "CanRename"')
    fields.append('I."CanAddChild" AS "CanAddChild"')
    fields.append('I."Size" AS "Size"')
    fields.append('I."IsInCache" AS "IsInCache"')
    fields.append('I."Updated" AS "Updated"')
    fields.append('I."TimeStamp" AS "TimeStamp"')
    fields.append('FALSE AS "IsVersionable"')
    fields.append('CONCAT(\'%s://\', CONCAT(U."UserName", CONCAT(\'/\', I."FileId"))) AS "TitleOnServer"' % scheme)
    fields.append('CONCAT(\'%s://\', CONCAT(U."UserName", CONCAT(\'/\', I."FileId"))) AS "BaseURI"' % scheme)
    fields.append('CONCAT(\'%s://\', CONCAT(U."UserName", CONCAT(\'/\', I."FileId"))) AS "TargetURL"' % scheme)
    fields.append('CONCAT(\'%s://\', CONCAT(U."UserName", CONCAT(\'/\', I."FileId"))) AS "CasePreservingURL"' % scheme)
    return fields

def _getInsertQueryFields():
    fields = []
    fields.append('"FileId"')
    fields.append('"IsFolder"')
    fields.append('"Title"')
    fields.append('"DateCreated"')
    fields.append('"DateModified"')
    fields.append('"ContentType"')
    fields.append('"MediaType"')
    fields.append('"IsReadOnly"')
    fields.append('"CanRename"')
    fields.append('"CanAddChild"')
    fields.append('"Size"')
    fields.append('"TimeStamp"')
    fields.append('"IsInCache"')
    return fields

def _getUpdateQueryFields():
    fields = []
    fields.append('"IsFolder"')
    fields.append('"Title"')
    fields.append('"DateCreated"')
    fields.append('"DateModified"')
    fields.append('"ContentType"')
    fields.append('"MediaType"')
    fields.append('"IsReadOnly"')
    fields.append('"CanRename"')
    fields.append('"CanAddChild"')
    fields.append('"Size"')
    fields.append('"TimeStamp"')
    fields.append('"IsInCache"')
    fields.append('"Updated"')
    return fields

def _getSelectQuery(scheme):
    fields = _getSelectQueryFields(scheme)
    query = 'SELECT %s FROM "Item" AS I JOIN "User" AS U ON U."UserName" = ? LEFT JOIN "Parent" AS P ON I."FileId" = P."FileId" WHERE I."FileId" = ?' % ', '.join(fields)
    return query

def _getInsertQuery():
    fields = _getInsertQueryFields()
    marks = getMarks(fields)
    query = 'INSERT INTO "Item" (%s) VALUES (%s)' % (', '.join(fields), ', '.join(marks))
    return query

def _getUpdateQuery():
    fields = _getUpdateQueryFields()
    fieldmarks = getFieldMarks(fields)
    query = 'UPDATE "Item" SET %s WHERE "FileId" = ?' % ', '.join(fieldmarks)
    return query

def _getContentType(result):
    mime = 'application/octet-stream'
    content = 'application/vnd.google-apps.file'
    if 'mimeType' in result:
        mime = result['mimeType']
        if mime == g_folder:
            if 'parents' not in result:
                content = 'application/vnd.google-apps.folder-root'
            else:
                content = g_folder
        elif mime == 'application/vnd.google-apps.drive-sdk':
            content = 'application/vnd.google-apps.drive-sdk'
        elif mime.startswith('application/vnd.google-apps.document'):
            content = 'application/vnd.google-apps.document'
        elif mime.startswith('application/vnd.oasis.opendocument'):
            content = 'application/vnd.oasis.opendocument'
    return mime, content
