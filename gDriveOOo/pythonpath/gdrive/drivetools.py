#!
# -*- coding: utf_8 -*-

import uno

import datetime


g_scheme = 'vnd.google-apps'    #vnd.google-apps

g_plugin = 'com.gmail.prrvchr.extensions.gDriveOOo'
g_provider = 'com.gmail.prrvchr.extensions.CloudUcpOOo'

g_host = 'www.googleapis.com'
g_version = 'v3'
g_url = 'https://%s/drive/%s/' % (g_host, g_version)
g_upload = 'https://%s/upload/drive/%s/files' % (g_host, g_version)

g_userfields = 'user(displayName,permissionId,emailAddress)'
g_capabilityfields = 'canEdit,canRename,canAddChildren,canReadRevisions'
g_itemfields = 'id,parents,name,mimeType,size,createdTime,modifiedTime,trashed,capabilities(%s)' % g_capabilityfields
g_childfields = 'kind,nextPageToken,files(%s)' % g_itemfields

# Minimun chunk: 262144 (256Ko) no more uploads if less... (must be a multiple of 64Ko (and 32Ko))
g_chunk = 262144
g_length = 32768  # InputStream (Downloader) maximum 'Buffers' size
g_pages = 100
g_timeout = (15, 60)
g_IdentifierRange = (10, 50)

g_office = 'application/vnd.oasis.opendocument'
g_folder = 'application/vnd.google-apps.folder'
g_link = 'application/vnd.google-apps.drive-sdk'
g_doc_map = {'application/vnd.google-apps.document':     'application/vnd.oasis.opendocument.text',
             'application/vnd.google-apps.spreadsheet':  'application/x-vnd.oasis.opendocument.spreadsheet',
             'application/vnd.google-apps.presentation': 'application/vnd.oasis.opendocument.presentation',
             'application/vnd.google-apps.drawing':      'application/pdf'}


def getUser(session):
    user, root = None, None
    url = '%sabout' % g_url
    params = {'fields': g_userfields}
    with session.get(url, params=params, timeout=g_timeout) as r:
        print("drivetools.getUser(): %s - %s" % (r.status_code, r.json()))
        if r.status_code == session.codes.ok:
            user = r.json().get('user')
            root = getItem(session, 'root')
    return user, root

def getItem(session, id):
    url = '%sfiles/%s' % (g_url, id)
    params = {'fields': g_itemfields}
    with session.get(url, params=params, timeout=g_timeout) as r:
        print("drivetools.getItem(): %s - %s" % (r.status_code, r.json()))
        if r.status_code == session.codes.ok:
            return r.json()
    return None

def getUploadLocation(session, id, data, mimetype, new, size):
    url = g_upload  if new else '%s/%s' % (g_upload, id)
    params = {'uploadType': 'resumable'}
    headers = {'X-Upload-Content-Length': '%s' % size}
    if new or mimetype:
        headers['X-Upload-Content-Type'] = mimetype
    print("drivetools.getUploadLocation()1: %s - %s" % (url, id))
    method = 'POST' if new else 'PATCH'
    with session.request(method, url, params=params, headers=headers, json=data) as r:
        print("drivetools.getUploadLocation()2 %s - %s" % (r.status_code, r.headers))
        print("drivetools.getUploadLocation()3 %s - %s" % (r.content, data))
        if r.status_code == session.codes.ok and 'Location' in r.headers:
            return r.headers['Location']
    return None

def updateItem(session, id, data, new):
    url = '%sfiles' % g_url if new else '%sfiles/%s' % (g_url, id)
    method = 'POST' if new else 'PATCH'
    with session.request(method, url, json=data) as r:
        print("drivetools.updateItem()1 %s - %s" % (r.status_code, r.headers))
        print("drivetools.updateItem()2 %s - %s" % (r.content, data))
        if r.status_code == session.codes.ok:
            return id
    return False

def selectChildId(connection, userid, parent, title):
    id = None
    call = connection.prepareCall('CALL "selectChildId"(?, ?, ?)')
    call.setString(1, userid)
    call.setString(2, parent)
    call.setString(3, title)
    result = call.executeQuery()
    if result.next():
        id = result.getString(1)
    call.close()
    return id

def isIdentifier(connection, userid, id):
    retreived = False
    call = connection.prepareCall('CALL "isIdentifier"(?, ?)')
    call.setString(1, userid)
    call.setString(2, id)
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

def getNewIdentifier(connection, userid):
    select = connection.prepareCall('CALL "selectIdentifier"(?)')
    select.setString(1, userid)
    result = select.executeQuery()
    if result.next():
        id = result.getString(1)
    select.close()
    return id

def _countIdentifier(connection, id):
    count = 0
    call = connection.prepareCall('CALL "countIdentifier"(?)')
    call.setString(1, id)
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

def setJsonData(call, data, parser, timestamp, index=1):
    call.setString(index, data.get('id'))
    index += 1
    call.setString(index, data.get('name'))
    index += 1
    call.setTimestamp(index, parser(data.get('createdTime', timestamp)))
    index += 1
    call.setTimestamp(index, parser(data.get('modifiedTime', timestamp)))
    index += 1
    call.setString(index, data.get('mimeType', 'application/octet-stream'))
    index += 1
    call.setLong(index, int(data.get('size', 0)))
    index += 1
    call.setBoolean(index, data.get('trashed', False))
    index += 1
    call.setBoolean(index, data.get('capabilities', {}).get('canAddChildren', False))
    index += 1
    call.setBoolean(index, data.get('capabilities', {}).get('canRename', False))
    index += 1
    call.setBoolean(index, not data.get('capabilities', {}).get('canEdit', False))
    index += 1
    call.setBoolean(index, data.get('capabilities', {}).get('canReadRevisions', False))
    index += 1
    return index
