#!
# -*- coding: utf_8 -*-


from .dbtools import getMarks, parseDateTime


def getUserInsertStatement(connection):
    query = _getInsertQuery()
    return connection.prepareStatement(query)

def getUserSelectStatement(connection):
    query = _getSelectQuery()
    return connection.prepareStatement(query)

def executeUserInsertStatement(insert, username, id):
    insert.setString(1, username)
    insert.setString(2, id)
    insert.setTimestamp(3, parseDateTime())
    return insert.executeUpdate()

def _getInsertQueryFields():
    fields = ['"UserName"']
    fields.append('"RootId"')
    fields.append('"TimeStamp"')
    return fields

def _getInsertQuery():
    fields = _getInsertQueryFields()
    marks = getMarks(fields)
    query = 'INSERT INTO "User" (%s) VALUES (%s)' % (', '.join(fields), ', '.join(marks))
    return query

def _getSelectQuery():
    query = 'Select "RootId" FROM "User" WHERE "UserName" = ?'
    return query
