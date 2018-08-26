#!
# -*- coding: utf_8 -*-

from .google import IdGenerator


def getCountOfIdentifier(connection, username):
    count = 0
    call = connection.prepareCall('CALL "getCountOfIdentifier"(?)')
    call.setString(1, username)
    result = call.executeQuery()
    if result.next():
        count = result.getLong(1)
    call.close()
    return count

def getIdDelete(connection):
    query = 'DELETE FROM "Identifiers" WHERE "UserName" = ? AND "Id" = ?;'
    return connection.prepareStatement(query)

def getIdSelect(connection):
    query = 'SELECT "Id", "TimeStamp" FROM "Identifiers" WHERE "InUse" = FALSE AND "UserName"= ? ORDER BY "TimeStamp" LIMIT 1;'
    return connection.prepareStatement(query)

def getIdInsert(connection):
    query = 'INSERT INTO "Identifiers" ("UserName", "Id") VALUES (?, ?);'
    return connection.prepareStatement(query)

def getIdUpdate(connection):
    query = 'UPDATE "Identifiers" SET "InUse" = TRUE, "TimeStamp" = CURRENT_TIMESTAMP(3) WHERE "Id" = ?;'
    return connection.prepareStatement(query)

def updateIdentifier(update, id):
    update.setString(1, id)
    return update.executeUpdate()
    
def getNewId(ctx, scheme, username, select, insert):
    select.setString(1, username)
    result = select.executeQuery()
    if result.next():
        id = result.getString(1)
    else:
        id = _insertNewId(ctx, scheme, username, insert, select)
    result.close()
    return id

def _insertNewId(ctx, scheme, username, insert, select):
    insert.setString(1, username)
    for id in IdGenerator(ctx, scheme, username):
        insert.setString(2, id)
        insert.executeUpdate()
    result = select.executeQuery()
    if result.next():
        id = result.getString(1)
    result.close()
    return id
