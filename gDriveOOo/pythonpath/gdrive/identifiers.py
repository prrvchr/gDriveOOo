#!
# -*- coding: utf_8 -*-

from .google import IdGenerator

g_IdentifierRange = (10, 50)


def isIdentifier(connection, identifier):
    retreived = False
    call = connection.prepareCall('CALL "isIdentifier"(?, ?)')
    call.setString(1, identifier.UserId)
    call.setString(2, identifier.Id)
    result = call.executeQuery()
    if result.next():
        retreived = result.getBoolean(1)
    call.close()
    return retreived

def checkIdentifiers(connection, session, userid):
    result = True
    if _countIdentifier(connection, userid) < min(g_IdentifierRange):
        result = _insertIdentifier(connection, session, userid, max(g_IdentifierRange))
    return result

def getIdentifier(connection, userid):
    select = connection.prepareCall('CALL "selectIdentifier"(?)')
    select.setString(1, userid)
    result = select.executeQuery()
    if result.next():
        id = result.getString(1)
    select.close()
    return id

def updateIdentifier(connection, userid, id):
    update = connection.prepareCall('CALL "updateIdentifier"(?, ?, ?)')
    update.setString(1, userid)
    update.setString(2, id)
    update.execute()
    return update.getLong(3)

def _countIdentifier(connection, userid):
    count = 0
    call = connection.prepareCall('CALL "countIdentifier"(?)')
    call.setString(1, userid)
    result = call.executeQuery()
    if result.next():
        count = result.getLong(1)
    call.close()
    return count

def _insertIdentifier(connection, session, userid, count):
    insert = connection.prepareCall('CALL "insertIdentifier"(?, ?, ?)')
    insert.setString(1, userid)
    result = all(_doInsert(insert, id) for id in IdGenerator(session, count))
    insert.close()
    return result

def _doInsert(insert, id):
    insert.setString(2, id)
    insert.execute()
    return insert.getLong(3)
