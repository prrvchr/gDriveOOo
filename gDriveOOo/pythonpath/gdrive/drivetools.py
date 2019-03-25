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


g_datetime = '%Y-%m-%dT%H:%M:%S.%fZ'

RETRIEVED = 0
CREATED = 1
FOLDER = 2
FILE = 4
RENAMED = 8
REWRITED = 16
TRASHED = 32


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

def parseDateTime(timestr=None):
    if timestr is None:
        t = datetime.datetime.now()
    else:
        t = datetime.datetime.strptime(timestr, g_datetime)
    return _getDateTime(t.microsecond, t.second, t.minute, t.hour, t.day, t.month, t.year)

def unparseDateTime(t=None):
    if t is None:
        return datetime.datetime.now().strftime(g_datetime)
    millisecond = 0
    if hasattr(t, 'HundredthSeconds'):
        millisecond = t.HundredthSeconds * 10
    elif hasattr(t, 'NanoSeconds'):
        millisecond = t.NanoSeconds // 1000000
    return '%s-%s-%sT%s:%s:%s.%03dZ' % (t.Year, t.Month, t.Day, t.Hours, t.Minutes, t.Seconds, millisecond)

def _getDateTime(microsecond=0, second=0, minute=0, hour=0, day=1, month=1, year=1970, utc=True):
    t = uno.createUnoStruct('com.sun.star.util.DateTime')
    t.Year = year
    t.Month = month
    t.Day = day
    t.Hours = hour
    t.Minutes = minute
    t.Seconds = second
    if hasattr(t, 'HundredthSeconds'):
        t.HundredthSeconds = microsecond // 10000
    elif hasattr(t, 'NanoSeconds'):
        t.NanoSeconds = microsecond * 1000
    if hasattr(t, 'IsUTC'):
        t.IsUTC = utc
    return t
