#!
# -*- coding: utf_8 -*-

from .google import IdGenerator

import traceback

g_IdentifierRange = (10, 50)


def isIdentifier(connection, id):
    retreived = False
    call = connection.prepareCall('CALL "isIdentifier"(?)')
    call.setString(1, id)
    result = call.executeQuery()
    if result.next():
        retreived = result.getBoolean(1)
    call.close()
    return retreived

def checkIdentifiers(connection, user):
    try:
        result = True
        if _countIdentifier(connection) < min(g_IdentifierRange):
            result = _insertIdentifier(connection, user, max(g_IdentifierRange))
        return result
    except Exception as e:
        print("identifiers.checkIdentifiers().Error: %s - %s" % (e, traceback.print_exc()))

def getNewIdentifier(connection):
    select = connection.prepareCall('CALL "selectIdentifier"()')
    result = select.executeQuery()
    if result.next():
        id = result.getString(1)
    select.close()
    return id

def _countIdentifier(connection):
    count = 0
    call = connection.prepareCall('CALL "countIdentifier"()')
    result = call.executeQuery()
    if result.next():
        count = result.getLong(1)
    call.close()
    return count

def _insertIdentifier(connection, user, count):
    insert = connection.prepareCall('CALL "insertIdentifier"(?, ?, ?)')
    insert.setString(1, user.Id)
    result = all(_doInsert(insert, id) for id in IdGenerator(user.Session, count))
    insert.close()
    return result

def _doInsert(insert, id):
    insert.setString(2, id)
    insert.execute()
    return insert.getLong(3)
