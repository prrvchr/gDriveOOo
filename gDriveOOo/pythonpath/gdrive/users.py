#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getItemFromResult

def selectRoot(connection, username):
    retrived, root = False, {}
    call = connection.prepareCall('CALL "selectRoot"(?)')
    call.setString(1, username)
    result = call.executeQuery()
    if result.next():
        retrived, root = True, getItemFromResult(result)
    call.close()
    print("users.getRootFromUser(): %s - %s - %s" % (retrived, username, root))
    return retrived, username, root

def mergeRoot(connection, username, item):
    retrived, root = False, {}
    call = connection.prepareCall('CALL "mergeRoot"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    call.setString(1, username)
    call.setString(2, item['Id'])
    call.setString(3, item['Title'])
    call.setTimestamp(4, item['DateCreated'])
    call.setTimestamp(5, item['DateModified'])
    call.setString(6, item['MediaType'])
    call.setBoolean(7, item['IsReadOnly'])
    call.setBoolean(8, item['CanRename'])
    call.setBoolean(9, item['IsFolder'])
    call.setLong(10, item['Size'])
    call.setBoolean(11, item['IsVersionable'])
    result = call.executeQuery()
    if result.next():
        retrived, root = True, getItemFromResult(result)
    call.close()
    print("users.mergeRoot(): %s - %s - %s" % (retrived, username, root))
    return retrived, root





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