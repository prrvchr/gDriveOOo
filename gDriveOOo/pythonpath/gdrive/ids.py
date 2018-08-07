#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getMarks
from .google import IdGenerator


def getNewId(ctx, scheme, username, connection):
    query = uno.getConstantByName('com.sun.star.sdb.CommandType.QUERY')
    select = connection.prepareCommand('getId', query)
    select.setString(1, username)
    result = select.executeQuery()
    if result.next():
        id = result.getColumns().getByName('Id').getString()
    else:
        id = _insertNewId(ctx, scheme, username, connection)
    return id

def _insertNewId(ctx, scheme, username, connection):
    insert = _getInsertStatement(connection, username)
    for id in IdGenerator(ctx, scheme, username):
        insert.setString(2, id)
        insert.executeUpdate()
    return id

def _getInsertStatement(connection, username):
    query = _getInsertQuery()
    statement = connection.prepareStatement(query)
    statement.setString(1, username)
    return statement

def _getDeleteStatement(connection):
    query = _getDeleteQuery()
    return connection.prepareStatement(query)

def _getInsertQueryFields():
    fields = ('"UserName"',
              '"Id"')
    return fields

def _getInsertQuery():
    fields = _getInsertQueryFields()
    marks = getMarks(fields)
    query = 'INSERT INTO "Id" (%s, "TimeStamp") VALUES (%s, NOW())' % (', '.join(fields), ', '.join(marks))
    return query

def _getDeleteQuery():
    query = 'DELETE FROM "Id" WHERE "UserName" = ? AND "Id" = ?'
    return query
