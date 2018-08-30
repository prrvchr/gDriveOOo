#!
# -*- coding: utf_8 -*-

from .google import IdGenerator

g_IdentifierRange = (10, 50)


def checkIdentifiers(ctx, scheme, connection, username):
    result = True
    if _countIdentifier(connection, username) < min(g_IdentifierRange):
        result = _insertIdentifier(ctx, scheme, connection, username, max(g_IdentifierRange))
    return result

def geIdentifier(connection, username):
    select = connection.prepareCall('CALL "selectIdentifier"(?)')
    select.setString(1, username)
    result = select.executeQuery()
    if result.next():
        id = result.getString(1)
    select.close()
    return id

def updateIdentifier(connection, username, id):
    update = connection.prepareCall('CALL "updateIdentifier"(?, ?, ?)')
    update.setString(1, username)
    update.setString(2, id)
    update.execute()
    return update.getLong(3)

def _countIdentifier(connection, username):
    count = 0
    call = connection.prepareCall('CALL "countIdentifier"(?)')
    call.setString(1, username)
    result = call.executeQuery()
    if result.next():
        count = result.getLong(1)
    call.close()
    return count

def _insertIdentifier(ctx, scheme, connection, username, count):
    insert = connection.prepareCall('CALL "insertIdentifier"(?, ?, ?)')
    insert.setString(1, username)
    result = all(_doInsert(insert, id) for id in IdGenerator(ctx, scheme, username, count))
    insert.close()
    return result

def _doInsert(insert, id):
    insert.setString(2, id)
    insert.execute()
    return insert.getLong(3)
