#!
# -*- coding: utf_8 -*-


from .dbtools import getMarks, parseDateTime
from .google import IdGenerator


def getIdSelectStatement(connection, username):
    query = _getSelectQuery()
    statement = connection.prepareStatement(query)
    statement.setString(1, username)
    return statement

def getNewId(authentication, statement, username):
    result = statement.executeQuery()
    if result.next():
        id = result.getColumns().getByName('Id').getString()
    else:
        id = _insertNewId(authentication, statement.getConnection(), username)
    return id

def _insertNewId(authentication, connection, username):
    insert = _getInsertStatement(connection, username)
    for id in IdGenerator(authentication):
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
    fields = ['"UserName"']
    fields.append('"Id"')
    return fields

def _getInsertQuery():
    fields = _getInsertQueryFields()
    marks = getMarks(fields)
    query = 'INSERT INTO "Id" (%s, "TimeStamp") VALUES (%s, NOW())' % (', '.join(fields), ', '.join(marks))
    return query

def _getSelectQuery():
    query = 'SELECT "Id" FROM "Id" WHERE "UserName" = ?'
    return query

def _getDeleteQuery():
    query = 'DELETE FROM "Id" WHERE "UserName" = ? AND "Id" = ?'
    return query
