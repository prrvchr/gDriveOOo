#!
# -*- coding: utf_8 -*-


from .dbtools import getMarks, parseDateTime


def getUserInsert(connection):
    query = _getInsertQuery()
    return connection.prepareStatement(query)

def executeUserInsert(insert, username, id):
    insert.setString(1, username)
    insert.setString(2, id)
    return insert.executeUpdate()

def _getInsertQueryFields():
    fields = ['"UserName"']
    fields.append('"RootId"')
    return fields

def _getInsertQuery():
    fields = _getInsertQueryFields()
    marks = getMarks(fields)
    query = 'INSERT INTO "User" (%s, "TimeStamp") VALUES (%s, NOW())' % (', '.join(fields), ', '.join(marks))
    return query
