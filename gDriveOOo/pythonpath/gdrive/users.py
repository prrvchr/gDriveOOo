#!
# -*- coding: utf_8 -*-

import uno


def getRootSelect(connection, username):
    columns = ', '.join(_getUserSelectColumns())
    query = 'SELECT %s FROM "Users" AS "U" JOIN "Items" AS "I" ON "U"."RootId" = "I"."Id" WHERE "U"."UserName" = ?' % columns
    select = connection.prepareStatement(query)
    select.setString(1, username)
    return select

def executeUserInsert(connection, username, id):
    query = 'INSERT INTO "Users" ("UserName", "RootId", "TimeStamp") VALUES (?, ?, NOW())'
    insert = connection.prepareStatement(query)
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
               '"I"."IsInCache" "IsInCache"')
    return columns