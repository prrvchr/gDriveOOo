#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.io import XActiveDataSource, XActiveDataSink, XActiveDataControl
from com.sun.star.io import XOutputStream, XInputStream, IOException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
from com.sun.star.connection import NoConnectException

from .dbtools import parseDateTime

import requests
import sys


if sys.version_info[0] < 3:
    requests.packages.urllib3.disable_warnings()

g_scheme = 'vnd.google-apps'
g_host = 'www.googleapis.com'
g_url = 'https://%s/drive/v3/' % g_host
g_upload = 'https://%s/upload/drive/v3/files' % g_host
g_userfields = 'user(displayName,permissionId,emailAddress)'
g_capabilityfields = 'canEdit,canRename,canAddChildren,canReadRevisions'
g_itemfields = 'id,parents,name,mimeType,size,createdTime,modifiedTime,capabilities(%s)' % g_capabilityfields
g_childfields = 'kind,nextPageToken,files(%s)' % g_itemfields
# Minimun chunk: 262144 no more upload if less... (must be a multiple of 64Ko)
g_chunk = 262144
g_pages = 100
g_timeout = (15, 60)
g_folder = 'application/vnd.google-apps.folder'
g_link = 'application/vnd.google-apps.drive-sdk'
g_doc = 'application/vnd.google-apps.'


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
        status = r.status_code
        if r.status_code == requests.codes.ok:
            result = r.json()
            if 'user' in result:
                user = _parseUser(result['user'])
                root = getItem(session, 'root')
    return user, root

def getItem(session, id):
    item = None
    url = '%sfiles/%s' % (g_url, id)
    params = {}
    params['fields'] = g_itemfields
    with session.get(url, params=params, timeout=g_timeout) as r:
        print("google.getItem(): %s - %s" % (r.status_code, r.json()))
        if r.status_code == requests.codes.ok:
            item = _parseItem(r.json(), parseDateTime())
    return item

def getUploadLocation(session, item, size):
    id = item['id']
    new = item['mode'] & 16 == 16
    data = None
    method = 'POST' if new else 'PATCH'
    url = g_upload  if new else '%s/%s' % (g_upload, id)
    params = {'uploadType': 'resumable'}
    headers = {'X-Upload-Content-Length': '%s' % size}
    if new:
        data = item['Data']
        data.update({'id': id, 'parents': item['parents']})
        headers['X-Upload-Content-Type'] = data['mimeType']
    #session.headers.update(headers)
    print("google.getUploadLocation()1: %s - %s" % (url, id))
    with session.request(method, url, params=params, headers=headers, json=data) as r:
        print("contenttools.getUploadLocation()2 %s - %s" % (r.status_code, r.headers))
        print("contenttools.getUploadLocation()3 %s - %s" % (r.content, data))
        if r.status_code == requests.codes.ok and 'Location' in r.headers:
            return r.headers['Location']
    return None

def updateItem(session, item):
    id = item['id']
    new = item['mode'] & 16 == 16
    data = item['Data']
    method = 'POST' if new else 'PATCH'
    url = '%sfiles' % g_url if new else '%sfiles/%s' % (g_url, id)
    if new:
        data.update({'id': id, 'parents': item['parents']})
    with session.request(method, url, json=data) as r:
        print("contenttools.updateItem()1 %s - %s" % (r.status_code, r.headers))
        print("contenttools.updateItem()2 %s - %s" % (r.content, data))
        if r.status_code == requests.codes.ok:
            return id
    return False


class IdGenerator():
    def __init__(self, session, count, space='drive'):
        print("google.IdGenerator.__init__()")
        self.session = session
        self.params = {'count': count, 'space': space}
        print("google.IdGenerator.__init__()")
    def __iter__(self):
        self.ids = self._getIds()
        return self
    def __next__(self):
        if self.ids:
            return self.ids.pop(0)
        raise StopIteration
    # for python v2.xx
    def next(self):
        return self.__next__()
    def _getIds(self):
        ids = []
        url = '%sfiles/generateIds' % g_url
        with self.session.get(url, params=self.params, timeout=g_timeout) as r:
            print("google.IdGenerator(): %s" % r.json())
            if r.status_code == requests.codes.ok:
                result = r.json()
                if 'ids' in result:
                    ids = result['ids']
        return ids


class ChildGenerator():
    def __init__(self, session, id):
        print("google.ChildGenerator.__init__()")
        self.session = session
        self.params = {'fields': g_childfields, 'pageSize': g_pages}
        self.params['q'] = "'%s' in parents" % id
        self.timestamp = parseDateTime()
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
            result = r.json()
            if 'files' in result:
                rows = [_parseItem(data, self.timestamp) for data in result['files']]
            if 'nextPageToken' in result:
                token = result['nextPageToken']
        return rows, token


class InputStream(unohelper.Base, XInputStream):
    def __init__(self, session, id, size, mimetype=None):
        self.session = session
        self.url = '%sfiles/%s' % (g_url, id) if size else '%sfiles/%s/export' % (g_url, id)
        self.size = size
        self.length = 32768
        self.mimetype = mimetype
        self.chunks = None
        print("google.InputStream.__init__()")

    #XInputStream
    def readBytes(self, sequence, length):
        # I assume that length is constant...
        if self.chunks is None:
            self.chunks = (s for c in ChunksDownloader(self.session, self.url, length, self.size, self.mimetype) for s in c)
        print("google.InputStream.readBytes() 1")
        sequence = uno.ByteSequence(next(self.chunks, b''))
        length = len(sequence)
        print("google.InputStream.readBytes() 2 %s" % (length, ))
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
    def __init__(self, session, url, length, size, mimetype=None):
        print("google.ChunkDownloader.__init__()")
        self.session = session
        self.url = url
        self.size = size
        self.length = length
        self.start, self.closed = 0, False
        self.headers = {}
        self.headers['Accept-Encoding'] = 'gzip'
        self.params = {'alt': 'media'} if mimetype is None else {'mimeType': mimetype}
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
        #self.headers['Content-Range'] = 'bytes */%s' % self.size
        #with self.session.put(self.url, headers=self.headers, timeout=g_timeout, auth=self.authentication) as r:
        #    print("google.OutputStream.__init__(): %s - %s" % (r.status_code, r.headers))
        #    if r.status_code == requests.codes.ok:
        #        if 'Range' in r.headers:
        #            self.start = int(r.headers['Range'].split('-')[-1]) +1
        #self.headers['Content-Type'] = mimetype

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
        self.session.close()
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
    def __init__(self, ctx, username=None):
        name = 'com.gmail.prrvchr.extensions.OAuth2OOo.OAuth2Service'
        self.service = ctx.ServiceManager.createInstanceWithContext(name, ctx)
        self.service.ResourceUrl = g_scheme
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


def _parseItem(data, timestamp):
    item = {}
    item['Id'] = data['id']
    item['Name'] = data['name']
    item['DateCreated'] = parseDateTime(data['createdTime']) if 'createdTime' in data else timestamp
    item['DateModified'] = parseDateTime(data['modifiedTime']) if 'modifiedTime' in data else timestamp
    item['MimeType'] = data['mimeType']
    item['Size'] = int(data['size']) if 'size' in data else 0
    item['Parents'] = tuple(data['parents']) if 'parents' in data else ()
    item['CanAddChild'] = _parseCapabilities(data, 'canAddChildren', False)
    item['CanRename'] = _parseCapabilities(data, 'canRename', False)
    item['IsReadOnly'] = not _parseCapabilities(data, 'canEdit', True)
    item['IsVersionable'] = _parseCapabilities(data, 'canReadRevisions', False)
    return item

def _parseUser(data):
    user = {}
    user['Id'] = data['permissionId']
    user['UserName'] = data['emailAddress']
    user['DisplayName'] = data['displayName']
    return user

def _parseCapabilities(data, capability, default):
    capacity = default
    if 'capabilities' in data:
        capabilities = data['capabilities']
        if capability in capabilities:
            capacity = capabilities[capability]
    return capacity
