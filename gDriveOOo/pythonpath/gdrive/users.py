#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getItemFromResult, parseDateTime

def selectRoot(connection, username):
    retrived, root = False, {}
    call = connection.prepareCall('CALL "getRoot"(?)')
    call.setString(1, username)
    result = call.executeQuery()
    if result.next():
        retrived, root = True, getItemFromResult(result)
    call.close()
    print("users.getRootFromUser(): %s - %s - %s" % (retrived, username, root))
    return retrived, username, root

def mergeRoot(connection, username, json):
    retrived, root = False, {}
    timestamp = parseDateTime()
    call = connection.prepareCall('CALL "mergeRoot"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    call.setString(1, username)
    call.setString(2, json['id'])
    call.setString(3, json['name'])
    call.setTimestamp(4, parseDateTime(json['createdTime']) if 'createdTime' in json else timestamp)
    call.setTimestamp(5, parseDateTime(json['modifiedTime']) if 'modifiedTime' in json else timestamp)
    call.setString(6, json['mimeType'])
    call.setBoolean(7, not getCapabilities(json, 'canEdit', True))
    call.setBoolean(8, getCapabilities(json, 'canRename', False))
    call.setBoolean(9, getCapabilities(json, 'canAddChildren', False))
    call.setLong(10, int(json['size']) if 'size' in json else 0)
    call.setBoolean(11, getCapabilities(json, 'canReadRevisions', False))
    result = call.executeQuery()
    if result.next():
        retrived, root = True, getItemFromResult(result)
    call.close()
    print("users.mergeRoot(): %s - %s - %s" % (retrived, username, root))
    return retrived, root

def getCapabilities(json, capability, default):
    capacity = default
    if 'capabilities' in json:
        capabilities = json['capabilities']
        if capability in capabilities:
            capacity = capabilities[capability]
    return capacity

def getUserSelect(connection):
    columns = ', '.join(_getUserSelectColumns())
    query = 'SELECT %s FROM "Users" AS "U" JOIN "Items" AS "I" ON "U"."RootId" = "I"."Id" WHERE "U"."UserName" = ?;' % columns
    return connection.prepareStatement(query)

def executeUserInsert(ctx, insert, username, id):
    print("users.executeUserInsert(): %s - %s" % (username, id))
    mri = ctx.ServiceManager.createInstance('mytools.Mri')
    mri.inspect(insert)
    insert.setString(1, username)
    insert.setString(2, id)
    return insert.executeUpdate()

def _getUserSelectColumns():
    columns = ('"I"."Id" "Id"',
               '"I"."Title" "Title"',
               '"I"."DateCreated" "DateCreated"',
               '"I"."DateModified" "DateModified"',
               '"I"."MediaType" "MediaType"',
               '"I"."IsReadOnly" "IsReadOnly"',
               '"I"."CanRename" "CanRename"',
               '"I"."CanAddChild" "CanAddChild"',
               '"I"."Size" "Size"',
               '"I"."IsRead" "IsRead"')
    return columns