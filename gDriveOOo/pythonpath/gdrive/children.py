#!
# -*- coding: utf_8 -*-

import uno

from .google import ChildGenerator
from .google import g_folder
from .items import mergeJsonItemCall
from .items import mergeJsonItem


def isChildId(identifier, id):
    ischild = False
    call = identifier.User.Connection.prepareCall('CALL "isChildId"(?, ?)')
    call.setString(1, identifier.Id)
    call.setString(2, id)
    result = call.executeQuery()
    if result.next():
        ischild = result.getBoolean(1)
    call.close()
    return ischild

def selectChildId(connection, parent, uri):
    id = None
    call = connection.prepareCall('CALL "selectChildId"(?, ?)')
    call.setString(1, parent)
    call.setString(2, uri)
    result = call.executeQuery()
    if result.next():
        id = result.getString(1)
    call.close()
    return id

def selectChildUniqueId(identifier, title):
    id = None
    call = identifier.User.Connection.prepareCall('CALL "selectChildUniqueId"(?, ?, ?)')
    call.setString(1, identifier.User.Id)
    call.setString(2, identifier.Id)
    call.setString(3, title)
    result = call.executeQuery()
    if result.next():
        id = result.getString(1)
    call.close()
    return id

def countChildTitle(identifier, title):
    count = 1
    call = identifier.User.Connection.prepareCall('CALL "countChildTitle"(?, ?, ?)')
    call.setString(1, identifier.User.Id)
    call.setString(2, identifier.Id)
    call.setString(3, title)
    result = call.executeQuery()
    if result.next():
        count = result.getLong(1)
    call.close()
    return count

def updateChildren(session, connection, userid, id):
    merge, index = mergeJsonItemCall(connection, userid)
    update = all(mergeJsonItem(merge, item, index) for item in ChildGenerator(session, id))
    merge.close()
    return update

def getChildSelect(identifier):
    # LibreOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
    # OpenOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
    index, select = 1, identifier.User.Connection.prepareCall('CALL "selectChild"(?, ?, ?, ?, ?, ?)')
    # select return RowCount as OUT parameter in select.getLong(index)!!!
    # Never managed to run the next line:
    # select.ResultSetType = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE')
    # selectChild(IN ID VARCHAR(100),IN URL VARCHAR(250),IN MODE SMALLINT,OUT ROWCOUNT SMALLINT)
    select.setString(index, identifier.User.Id)
    index += 1
    select.setString(index, identifier.Id)
    index += 1
    # "TargetURL" is done by CONCAT(BaseURL,'/',Title or Id)...
    select.setString(index, identifier.BaseURL)
    index += 1
    # "IsFolder" is done by comparing MimeType with g_folder 'application/vnd.google-apps.folder' ...
    select.setString(index, g_folder)
    index += 1
    select.setLong(index, identifier.User.Mode)
    index += 1
    return index, select
