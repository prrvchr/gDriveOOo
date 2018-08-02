#!
# -*- coding: utf_8 -*-

import uno

from .dbtools import getMarks, parseDateTime
from .items import getItemInsert, getItemUpdate, executeItemUpdate
from .google import ChildGenerator
from .unotools import getResourceLocation, createService



def updateChildren(ctx, scheme, username, id):
    url = getResourceLocation(ctx, '%s.odb' % scheme)
    db = createService('com.sun.star.sdb.DatabaseContext').getByName(url)
    connection = db.getConnection('', '')
    timestamp = parseDateTime()
    iteminsert = getItemInsert(connection)
    itemupdate = getItemUpdate(connection)
    childdelete = _getChildDelete(connection)
    childinsert = _getChildInsert(connection)
    for result in ChildGenerator(ctx, scheme, username, id):
        if 'id' in result:
            executeItemUpdate(iteminsert, itemupdate, result, False, timestamp)
            _updateParent(childdelete, childinsert, result, timestamp)
    connection.close()

def _getChildDelete(connection):
    query = _getDeleteQuery()
    return connection.prepareStatement(query)

def _getChildInsert(connection):
    query = _getInsertQuery()
    return connection.prepareStatement(query)

def insertParent(connection, arguments):
    query = _getInsertQuery()
    insert = connection.prepareStatement(query)
    insert.setString(1, arguments['Id'])
    insert.setString(2, arguments['ParentId'])
    insert.setTimestamp(3, parseDateTime())
    insert.executeUpdate()

def _getInsertQueryFields():
    fields = []
    fields.append('"Id"')
    fields.append('"ParentId"')
    fields.append('"TimeStamp"')
    return fields

def _getInsertQuery():
    fields = _getInsertQueryFields()
    marks = getMarks(fields)
    query = 'INSERT INTO "Parent" (%s) VALUES (%s)' % (', '.join(fields), ', '.join(marks))
    return query

def _getDeleteQuery():
    query = 'DELETE FROM "Parent" WHERE "Id" = ?'
    return query

def _updateParent(delete, insert, result, timestamp):
    id = result['id']
    delete.setString(1, id)
    delete.executeUpdate()
    if 'parents' in result:
        for parent in result['parents']:
            insert.setString(1, id)
            insert.setString(2, parent)
            insert.setTimestamp(3, timestamp)
            insert.executeUpdate()
