#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.connection import NoConnectException
from com.sun.star.io import XOutputStream
from com.sun.star.io import XInputStream
from com.sun.star.io import IOException
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.ucb.ConnectionMode import OFFLINE

import requests
import sys
import datetime


if sys.version_info[0] < 3:
    requests.packages.urllib3.disable_warnings()

g_scheme = 'vnd.google-apps'    #vnd.google-apps
g_host = 'www.googleapis.com'

g_url = 'https://%s/drive/v3/' % g_host
g_upload = 'https://%s/upload/drive/v3/files' % g_host

g_userfields = 'user(displayName,permissionId,emailAddress)'
g_capabilityfields = 'canEdit,canRename,canAddChildren,canReadRevisions'
g_itemfields = 'id,parents,name,mimeType,size,createdTime,modifiedTime,trashed,capabilities(%s)' % g_capabilityfields
g_childfields = 'kind,nextPageToken,files(%s)' % g_itemfields

# Minimun chunk: 262144 (256Ko) no more uploads if less... (must be a multiple of 64Ko (and 32Ko))
g_chunk = 262144
g_pages = 100
g_timeout = (15, 60)

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


def getConnectionMode(ctx):
    connection, connector = None, ctx.ServiceManager.createInstance('com.sun.star.connection.Connector')
    try:
        connection = connector.connect('socket,host=%s,port=80' % g_host)
    except NoConnectException:
        pass
    if connection is not None:
        connection.close()
        return ONLINE
    return OFFLINE

def getUser(session):
    user, root = None, None
    url = '%sabout' % g_url
    params = {'fields': g_userfields}
    with session.get(url, params=params, timeout=g_timeout) as r:
        print("google.getUser(): %s - %s" % (r.status_code, r.json()))
        if r.status_code == requests.codes.ok:
            user = r.json().get('user')
            root = getItem(session, 'root')
    return user, root

def getItem(session, id):
    url = '%sfiles/%s' % (g_url, id)
    params = {'fields': g_itemfields}
    with session.get(url, params=params, timeout=g_timeout) as r:
        print("google.getItem(): %s - %s" % (r.status_code, r.json()))
        if r.status_code == requests.codes.ok:
            return r.json()
    return None

def getUploadLocation(session, id, data, mimetype, new, size):
    url = g_upload  if new else '%s/%s' % (g_upload, id)
    params = {'uploadType': 'resumable'}
    headers = {'X-Upload-Content-Length': '%s' % size}
    if new or mimetype:
        headers['X-Upload-Content-Type'] = mimetype
    #session.headers.update(headers)
    print("google.getUploadLocation()1: %s - %s" % (url, id))
    method = 'POST' if new else 'PATCH'
    with session.request(method, url, params=params, headers=headers, json=data) as r:
        print("contenttools.getUploadLocation()2 %s - %s" % (r.status_code, r.headers))
        print("contenttools.getUploadLocation()3 %s - %s" % (r.content, data))
        if r.status_code == requests.codes.ok and 'Location' in r.headers:
            return r.headers['Location']
    return None

def updateItem(session, id, data, new):
    url = '%sfiles' % g_url if new else '%sfiles/%s' % (g_url, id)
    with session.request('POST' if new else 'PATCH', url, json=data) as r:
        print("contenttools.updateItem()1 %s - %s" % (r.status_code, r.headers))
        print("contenttools.updateItem()2 %s - %s" % (r.content, data))
        if r.status_code == requests.codes.ok:
            return id
    return False


class IdGenerator():
    def __init__(self, session, count, space='drive'):
        print("google.IdGenerator.__init__()")
        self.ids = []
        url = '%sfiles/generateIds' % g_url
        params = {'count': count, 'space': space}
        with session.get(url, params=params, timeout=g_timeout) as r:
            print("google.IdGenerator(): %s" % r.json())
            if r.status_code == requests.codes.ok:
                self.ids = r.json().get('ids', [])
        print("google.IdGenerator.__init__()")
    def __iter__(self):
        return self
    def __next__(self):
        if self.ids:
            return self.ids.pop(0)
        raise StopIteration
    # for python v2.xx
    def next(self):
        return self.__next__()


class ChildGenerator():
    def __init__(self, session, id):
        print("google.ChildGenerator.__init__()")
        self.session = session
        self.params = {'fields': g_childfields, 'pageSize': g_pages}
        self.params['q'] = "'%s' in parents" % id
        self.timestamp = unparseDateTime()
        self.url = '%sfiles' % g_url
        print("google.ChildGenerator.__init__()")
    def __iter__(self):
        self.rows, self.token = self._getChunk()
        return self
    def __next__(self):
        if self.rows:
            return self.rows.pop(0)
        elif self.token:
            self.rows, self.token = self._getChunk(self.token)
            return self.rows.pop(0)
        raise StopIteration
    # for python v2.xx
    def next(self):
        return self.__next__()
    def _getChunk(self, token=None):
        self.params['pageToken'] = token
        rows = []
        token = None
        r = self.session.get(self.url, params=self.params, timeout=g_timeout)
        print("google.ChildGenerator(): %s" % r.json())
        if r.status_code == requests.codes.ok:
            rows = r.json().get('files', [])
            token = r.json().get('nextPageToken', None)
        return rows, token


class InputStream(unohelper.Base, XInputStream):
    def __init__(self, session, id, size, mimetype):
        self.session = session
        self.length = 32768
        url = '%sfiles/%s/export' % (g_url, id) if mimetype else '%sfiles/%s' % (g_url, id)
        params = {'mimeType': mimetype} if mimetype else {'alt': 'media'}
        self.chunks = (s for c in ChunksDownloader(self.session, url, params, size, self.length) for s in c)
        print("google.InputStream.__init__()")

    #XInputStream
    def readBytes(self, sequence, length):
        # I assume that 'length' is constant...and is multiple of 'self.length'
        sequence = uno.ByteSequence(b'')
        while length > 0:
            sequence += uno.ByteSequence(next(self.chunks, b''))
            length -= self.length
        length = len(sequence)
        return length, sequence
    def readSomeBytes(self, sequence, length):
        return self.readBytes(sequence, length)
    def skipBytes(self, length):
        pass
    def available(self):
        return g_chunk
    def closeInput(self):
        self.session.close()


class ChunksDownloader():
    def __init__(self, session, url, params, size, length):
        print("google.ChunkDownloader.__init__()")
        self.session = session
        self.url = url
        self.size = size
        self.length = length
        self.start, self.closed = 0, False
        self.headers = {'Accept-Encoding': 'gzip'}
        self.params = params 
        print("google.ChunkDownloader.__init__()")
    def __iter__(self):
        return self
    def __next__(self):
        if self.closed:
            raise StopIteration
        print("google.ChunkDownloader.__next__() 1")
        end = g_chunk
        if self.size:
            end = min(self.start + g_chunk, self.size - self.start)
            self.headers['Range'] = 'bytes=%s-%s' % (self.start, end -1)
        print("google.ChunkDownloader.__next__() 2: %s" % (self.headers, ))
        r = self.session.get(self.url, headers=self.headers, params=self.params, timeout=g_timeout, stream=True)
        print("google.ChunkDownloader.__next__() 3: %s - %s" % (r.status_code, r.headers))
        if r.status_code == requests.codes.partial_content:
            self.start += int(r.headers.get('Content-Length', end))
            self.closed = self.start == self.size
            print("google.ChunkDownloader.__next__() 4 %s - %s" % (self.closed, self.start))
        elif  r.status_code == requests.codes.ok:
            self.start += int(r.headers.get('Content-Length', end))
            self.closed = True
            print("google.ChunkDownloader.__next__() 5 %s - %s" % (self.closed, self.start))
        else:
            raise IOException('Error Downloading file...', self)
        return r.iter_content(self.length)
    # for python v2.xx
    def next(self):
        return self.__next__()


class OutputStream(unohelper.Base, XOutputStream):
    def __init__(self, session, url, size):
        self.session = session
        self.url = url
        self.size = size
        self.buffers = uno.ByteSequence(b'')
        self.start = 0
        self.closed, self.flushed, self.chunked = False, False, size >= g_chunk

    # XOutputStream
    def writeBytes(self, sequence):
        if self.closed:
            raise IOException('OutputStream is closed...', self)
        self.buffers += sequence
        length = len(self.buffers)
        if length >= g_chunk and not self._isWrite(length):
            raise IOException('Error Uploading file...', self)
        else:
            print("google.OutputStream.writeBytes() Bufferize: %s - %s" % (self.start, length))
        return
    def flush(self):
        print("google.OutputStream.flush()")
        if self.closed:
            raise IOException('OutputStream is closed...', self)
        if not self.flushed and not self._flush():
            raise IOException('Error Uploading file...', self)
    def closeOutput(self):
        print("google.OutputStream.closeOutput()")
        if not self.flushed and not self._flush():
            raise IOException('Error Uploading file...', self)
        #self.session.close()
        self.closed = True
    def _flush(self):
        self.flushed = True
        length = len(self.buffers)
        return self._isWrite(length)
    def _isWrite(self, length):
        print("google.OutputStream._write() 1: %s" % (self.start, ))
        headers = None
        if self.chunked:
            end = self.start + length -1
            headers = {'Content-Range': 'bytes %s-%s/%s' % (self.start, end, self.size)}
        r = self.session.put(self.url, headers=headers, data=self.buffers.value)
        print("google.OutputStream._write() 2: %s" % (r.request.headers, ))
        print("google.OutputStream._write() 3: %s - %s" % (r.status_code, r.headers))
        print("google.OutputStream._write() 4: %s" % (r.content, ))
        if r.status_code == requests.codes.ok or r.status_code == requests.codes.created:
            self.start += int(r.request.headers['Content-Length'])
            self.buffers = uno.ByteSequence(b'')
            return True
        elif r.status_code == requests.codes.permanent_redirect:
            if 'Range' in r.headers:
                self.start += int(r.headers['Range'].split('-')[-1]) +1
                self.buffers = uno.ByteSequence(b'')
                return True
        return False


class OAuth2Ooo(object):
    def __init__(self, ctx, scheme, username=None):
        name = 'com.gmail.prrvchr.extensions.OAuth2OOo.OAuth2Service'
        self.service = ctx.ServiceManager.createInstanceWithContext(name, ctx)
        self.service.ResourceUrl = scheme
        if username is not None:
            self.service.UserName = username

    @property
    def UserName(self):
        return self.service.UserName
    @UserName.setter
    def UserName(self, username):
        self.service.UserName = username
    @property
    def Scheme(self):
        return self.service.ResourceUrl

    def __call__(self, request):
        request.headers['Authorization'] = 'Bearer %s' % self.service.Token
        return request


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
