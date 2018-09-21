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
    mode, connection = OFFLINE, None
    connector = ctx.ServiceManager.createInstance('com.sun.star.connection.Connector')
    try:
        connection = connector.connect('socket,host=%s,port=80' % g_host)
    except NoConnectException:
        pass
    if connection:
        connection.close()
        mode = ONLINE
    return mode

def getUser(session):
    status, user = False, {}
    url = '%sabout' % g_url
    params = {}
    params['fields'] = g_userfields
    r = session.get(url, params=params, timeout=g_timeout)
    print("google.getUser(): %s - %s" % (r.status_code, r.json()))
    status = r.status_code
    if status == requests.codes.ok:
        result = r.json()
        if 'user' in result:
            user = _parseUser(result['user'])
    return status, user

def getItem(session, id):
    status, item = False, {}
    url = '%sfiles/%s' % (g_url, id)
    params = {}
    params['fields'] = g_itemfields
    with session.get(url, params=params, timeout=g_timeout) as r:
        print("google.getItem(): %s - %s" % (r.status_code, r.json()))
        status = r.status_code
        if status == requests.codes.ok:
            item = _parseItem(r.json(), parseDateTime())
    return status, item

def getUploadLocation(session, id, data):
    location = None
    url = '%s/%s' % (g_upload, id) if data is None else g_upload
    method = 'PATCH' if data is None else 'POST'
    print("google.getUploadLocation()1: %s - %s" % (url, id))
    params = {'uploadType': 'resumable'}
    r = session.request(method, url, params=params, json=data)
    print("contenttools.getUploadLocation()2 %s - %s" % (r.status_code, r.headers))
    print("contenttools.getUploadLocation()3 %s - %s" % (r.content, data))
    if r.status_code == requests.codes.ok and 'Location' in r.headers:
        location = r.headers['Location']
    return location

def updateItem(session, id=None, data={}):
    result = False
    url = '%sfiles' % g_url if id is None else '%sfiles/%s' % (g_url, id)
    method = 'POST' if id is None else 'PATCH'
    r = session.request(method, url, json=data)
    if r.status_code == requests.codes.ok:
        result = True
    return result


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
    def __init__(self, ctx, scheme, username, id, size):
        self.session = requests.Session()
        self.session.auth = OAuth2Ooo(ctx, scheme, username)
        self.url = '%sfiles/%s' % (g_url, id)
        self.size = size
        self.start, self.sequences = 0, None

    #XInputStream
    def readBytes(self, sequence, length):
        # I assume that length is constant...
        if self.sequences is None:
            self.sequences = (s for chunks in ChunksDownloader(self.session, self.url, self.size, length) for s in chunks)
        print("google.InputStream.readBytes() 4")
        sequence = uno.ByteSequence(next(self.sequences, b''))
        length = len(sequence)
        self.start += length
        print("google.InputStream.readBytes() 6 %s - %s" % (length, self.start))
        return length, sequence
    def readSomeBytes(self, sequence, length):
        return self.readBytes(sequence, length)
    def skipBytes(self, length):
        if length <= self.available():
            self.start += length
    def available(self):
        return self.size - self.start
    def closeInput(self):
        self.session.close()
        self.start, self.sequences = 0, None


class ChunksDownloader():
    def __init__(self, session, url, size, length):
        print("google.ChunkDownloader.__init__()")
        self.session = session
        self.url = url
        self.size = size
        self.length = min(length, size)
        self.start = 0
        self.headers = {}
        self.headers['Content-Type'] = None
        self.headers['Accept-Encoding'] = 'gzip'
        self.params = {'alt': 'media'}
        print("google.ChunkDownloader.__init__()")
    def __iter__(self):
        return self
    def __next__(self):
        if self._available():
            print("google.ChunkDownloader.__next__() 1")
            chunk = min(self.size, g_chunk)
            self.headers['Range'] = 'bytes=%s-%s' % (self.start, self.start + chunk -1)
            print("google.ChunkDownloader.__next__() 2: %s" % (self.headers['Range'], ))
            r = self.session.get(self.url, headers=self.headers, params=self.params, timeout=g_timeout, stream=True)
            print("google.ChunkDownloader.__next__() 3: %s - %s" % (r.status_code, r.headers))
            if r.status_code == requests.codes.partial_content or r.status_code == requests.codes.ok:
                iterator = r.iter_content(self.length)
                self.start += chunk
                print("google.ChunkDownloader.__next__() 4 %s" % self.start)
                return iterator
            raise IOException('Error Downloading file...', self)
        raise StopIteration
    # for python v2.xx
    def next(self):
        return self.__next__()
    def _available(self):
        return self.size - self.start


class OutputStream(unohelper.Base, XOutputStream):
    def __init__(self, session, url, size):
        self.session = session
        self.url = url
        self.size = size
        self.buffers = uno.ByteSequence(b'')
        self.start = 0
        self.headers = {'Content-Type': 'application/octet-stream'}
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
        if self.chunked:
            end = self.start + length -1
            self.headers['Content-Range'] = 'bytes %s-%s/%s' % (self.start, end, self.size)
        r = self.session.put(self.url, headers=self.headers, data=self.buffers.value)
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
    def __init__(self, ctx, scheme=None, username=None):
        name = 'com.gmail.prrvchr.extensions.OAuth2OOo.OAuth2Service'
        self.service = ctx.ServiceManager.createInstanceWithContext(name, ctx)
        if scheme is not None:
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
    @Scheme.setter
    def Scheme(self, url):
        self.service.ResourceUrl = url

    def __call__(self, request):
        request.headers['Authorization'] = 'Bearer %s' % self.service.Token
        return request


def _parseItem(data, timestamp):
    item = {}
    item['Id'] = data['id']
    item['Name'] = data['name']
    item['DateCreated'] = parseDateTime(data['createdTime']) if 'createdTime' in data else timestamp
    item['DateModified'] = parseDateTime(data['modifiedTime']) if 'modifiedTime' in data else timestamp
    item['MediaType'] = data['mimeType']
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
