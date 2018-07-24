#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getMarks, parseDateTime
from .items import getItemInsertStatement, executeItemUpdateStatement
from .google import ChildGenerator


def updateChildren(authentication, connection, itemupdate, id):
    iteminsert = getItemInsertStatement(connection)
    childdelete = getChildDeleteStatement(connection)
    childinsert = getChildInsertStatement(connection)
    print("children.updateChildren() %s" % id)
    timestamp = parseDateTime()
    for result in ChildGenerator(authentication, id):
        if 'id' in result:
            executeItemUpdateStatement(iteminsert, itemupdate, result, False, timestamp)
            _updateParent(childdelete, childinsert, result, timestamp)

def getChildDeleteStatement(connection):
    query = _getDeleteQuery()
    return connection.prepareStatement(query)

def getChildInsertStatement(connection):
    query = _getInsertQuery()
    return connection.prepareStatement(query)

def getChildSelectStatement(connection, scheme, username=None, id=None):
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


def getChildStatementId(statement, id):
    statement.setString(1, id)
    return statement

def _getSelectQueryFields(scheme):
    fields = []
    fields.append('\'%s\' AS "Scheme"' % scheme)
    fields.append('U."UserName" AS "UserName"')
    fields.append('I."FileId" AS "FileId"')
    fields.append('I."IsFolder" AS "IsFolder"')
    fields.append('NOT I."IsFolder" AS "IsDocument"')
    fields.append('I."Title" AS "Title"')
    fields.append('I."DateCreated" AS "DateCreated"')
    fields.append('I."DateModified" AS "DateModified"')
    fields.append('I."ContentType" AS "ContentType"')
    fields.append('I."MediaType" AS "MediaType"')
    fields.append('I."IsReadOnly" AS "IsReadOnly"')
    fields.append('I."CanRename" AS "CanRename"')
    fields.append('I."CanAddChild" AS "CanAddChild"')
    fields.append('I."Size" AS "Size"')
    fields.append('CONCAT(\'%s://\', CONCAT(U."UserName", CONCAT(\'/\', I."FileId"))) AS "TargetURL"' % scheme)
    # CONVERT(0, BOOLEAN)
    fields.append('FALSE AS "IsHidden"')
    fields.append('FALSE AS "IsVolume"')
    fields.append('FALSE AS "IsRemote"')
    fields.append('FALSE AS "IsRemoveable"')
    fields.append('FALSE AS "IsFloppy"')
    fields.append('FALSE AS "IsCompactDisc"')
    return fields

def _getInsertQueryFields():
    fields = []
    fields.append('"FileId"')
    fields.append('"ParentId"')
    fields.append('"TimeStamp"')
    return fields

def _getSelectQuery(scheme):
    fields = _getSelectQueryFields(scheme)
    query = 'SELECT %s FROM "Item" AS I JOIN "Parent" AS P ON I."FileId" = P."FileId" JOIN "User" AS U ON U."UserName" = ?  WHERE P."ParentId" = ?' % ', '.join(fields)
    return query

def _getInsertQuery():
    fields = _getInsertQueryFields()
    marks = getMarks(fields)
    query = 'INSERT INTO "Parent" (%s) VALUES (%s)' % (', '.join(fields), ', '.join(marks))
    return query

def _getDeleteQuery():
    query = 'DELETE FROM "Parent" WHERE "FileId" = ?'
    return query

def _updateParent(delete, insert, result, timestamp):
    print("children._updateParent() 1")
    id = result['id']
    print("children._updateParent() 2")
    delete.setString(1, id)
    print("children._updateParent() 3")
    delete.executeUpdate()
    print("children._updateParent() 4")
    if 'parents' in result:
        for parent in result['parents']:
            print("children._updateParent() 5")
            insert.setString(1, id)
            print("children._updateParent() 6")
            insert.setString(2, parent)
            print("children._updateParent() 7")
            insert.setTimestamp(3, timestamp)
            print("children._updateParent() 8")
            insert.executeUpdate()
            print("children._updateParent() 9")
