#!
# -*- coding: utf_8 -*-

import uno

from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE

from .items import mergeJsonItemCall, mergeJsonItem
from .google import ChildGenerator, g_folder

import traceback


def isChildId(identifier, id):
    ischild = False
    call = identifier.Connection.prepareCall('CALL "isChildId"(?, ?)')
    call.setString(1, identifier.Id)
    call.setString(2, id)
    result = call.executeQuery()
    if result.next():
        ischild = result.getBoolean(1)
    call.close()
    return ischild

def selectChildId(identifier, title):
    id = None
    call = identifier.Connection.prepareCall('CALL "selectChildId"(?, ?)')
    call.setString(1, identifier.Id)
    call.setString(2, title)
    result = call.executeQuery()
    if result.next():
        id = result.getString(1)
    call.close()
    return id

def countChildTitle(identifier, title):
    count = None
    call = identifier.Connection.prepareCall('CALL "countChildTitle"(?, ?)')
    call.setString(1, identifier.Id)
    call.setString(2, title)
    result = call.executeQuery()
    if result.next():
        count = result.getLong(1)
    call.close()
    return count

def updateChildren(identifier):
    merge, index = mergeJsonItemCall(identifier.Connection, identifier.User.Id)
    with identifier.User.Session as session:
        update = all(mergeJsonItem(merge, item, index) for item in ChildGenerator(session, identifier.Id))
    merge.close()
    return update

def getChildSelect(identifier):
    # LibreOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
    # OpenOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
    index, select = 1, identifier.Connection.prepareCall('CALL "selectChild"(?, ?, ?, ?, ?)')
    # select return RowCount as OUT parameter in select.getLong(index)!!!
    # Never managed to run the next line:
    # select.ResultSetType = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_INSENSITIVE')
    # selectChild(IN ID VARCHAR(100),IN URL VARCHAR(250),IN MODE SMALLINT,OUT ROWCOUNT SMALLINT)
    select.setString(index, identifier.Id)
    index += 1
    # "TargetURL" is done by CONCAT(BaseURL,id,'/../',id)... The root uri already ends with a '/' ...
    uri = identifier.BaseURL
    select.setString(index, uri if uri.endswith('/') else '%s/' % uri)
    index += 1
    # "IsFolder" is done by comparing MimeType with g_folder 'application/vnd.google-apps.folder' ...
    select.setString(index, g_folder)
    index += 1
    select.setLong(index, identifier.Mode)
    index += 1
    return index, select
