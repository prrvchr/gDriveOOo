#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.io import XActiveDataSource, XActiveDataSink, XActiveDataControl, XInputStream

from .dbtools import parseDateTime

import requests
import sys


if sys.version_info[0] < 3:
    requests.packages.urllib3.disable_warnings()

g_url = 'https://www.googleapis.com/drive/v3/files'
g_itemfields = 'id,parents,name,mimeType,size,createdTime,modifiedTime,capabilities(canEdit,canRename,canAddChildren, canReadRevisions)'
g_childfields = 'kind,nextPageToken,files(%s)' % g_itemfields
g_chunk = 262144
g_pages = 100
g_count = 10
g_timeout = (15, 60)


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


def getItem(ctx, scheme, username, id):
    status = False
    item = {}
    authentication = OAuth2Ooo(ctx, scheme, username)
    url = '%s/%s' % (g_url, id)
    params = {}
    params['fields'] = g_itemfields
    session = requests.Session()
    with session.get(url, params=params, timeout=g_timeout, auth=authentication) as r:
        print("google.getItem(): %s - %s" % (r.status_code, r.json()))
        status = r.status_code
        if status == requests.codes.ok:
            item = getItemFromJson(r.json(), parseDateTime())
    return status, item

def getItemFromJson(json, timestamp):
    item = {}
    item['Id'] = json['id']
    item['Title'] = json['name']
    item['DateCreated'] = parseDateTime(json['createdTime']) if 'createdTime' in json else timestamp
    item['DateModified'] = parseDateTime(json['modifiedTime']) if 'modifiedTime' in json else timestamp
    item['MediaType'] = json['mimeType']
    item['IsReadOnly'] = not getCapabilities(json, 'canEdit', True)
    item['CanRename'] = getCapabilities(json, 'canRename', False)
    item['IsFolder'] = getCapabilities(json, 'canAddChildren', False)
    item['Size'] = int(json['size']) if 'size' in json else 0
    item['IsVersionable'] = getCapabilities(json, 'canReadRevisions', False)
    item['Parents'] = tuple(json['parents']) if 'parents' in json else ()
    return item

def getCapabilities(json, capability, default):
    capacity = default
    if 'capabilities' in json:
        capabilities = json['capabilities']
        if capability in capabilities:
            capacity = capabilities[capability]
    return capacity

class IdGenerator():
    def __init__(self, ctx, scheme, username, space='drive'):
        print("google.IdGenerator.__init__()")
        self.authentication = OAuth2Ooo(ctx, scheme, username)
        self.params = {'count': g_count, 'space': space}
        print("google.IdGenerator.__init__()")
    def __iter__(self):
        self.session = requests.Session()
        self.ids = self._getIds()
        return self
    def __next__(self):
        if self.ids:
            return self.ids.pop(0)
        raise StopIteration
    def next(self):
        return self.__next__()
    def _getIds(self):
        ids = []
        url = '%s/generateIds' % g_url
        with self.session.get(url, params=self.params, timeout=g_timeout, auth=self.authentication) as r:
            print("google.IdGenerator(): %s" % r.json())
            if r.status_code == requests.codes.ok:
                result = r.json()
                if 'ids' in result:
                    ids = result['ids']
        return ids


class ChildGenerator():
    def __init__(self, ctx, scheme, username, id):
        print("google.ChildGenerator.__init__()")
        self.authentication = OAuth2Ooo(ctx, scheme, username)
        self.params = {'fields': g_childfields, 'pageSize': g_pages}
        self.params['q'] = "'%s' in parents" % id
        self.timestamp = parseDateTime()
        print("google.ChildGenerator.__init__()")
    def __iter__(self):
        self.session = requests.Session()
        self.rows, self.token = self._getChunk()
        return self
    def __next__(self):
        if self.rows:
            return self.rows.pop(0)
        elif self.token:
            self.rows, self.token = self._getChunk(self.token)
            return self.rows.pop(0)
        raise StopIteration
    def next(self):
        return self.__next__()
    def _getChunk(self, token=None):
        self.params['pageToken'] = token
        rows = []
        token = None
        with self.session.get(g_url, params=self.params, timeout=g_timeout, auth=self.authentication) as r:
            print("google.ChildGenerator(): %s" % r.json())
            if r.status_code == requests.codes.ok:
                result = r.json()
                if 'files' in result:
                    rows = [getItemFromJson(j, self.timestamp) for j in result['files']]
                if 'nextPageToken' in result:
                    token = result['nextPageToken']
        return rows, token


class InputStream(unohelper.Base, XInputStream):
    def __init__(self, ctx, scheme, username, id, size):
        self.authentication = OAuth2Ooo(ctx, scheme, username)
        self.url = '%s/%s' % (g_url, id)
        self.size = size
        self.start = 0
        self.session = requests.Session()

    #XInputStream
    def readBytes(self, sequence, length):
        print("google.InputStream.start() 1")
        headers = {}
        headers['Content-Type'] = None
        headers['Accept-Encoding'] = 'gzip'
        params = {'alt': 'media'}
        chunk = min(self.available(), length)
        headers['Range'] = 'bytes=%s-%s' % (self.start, self.start + chunk -1)
        length, sequence = 0, uno.ByteSequence(b'')
        print("google.InputStream.start() 2: %s" % (headers['Range'], ))
        with self.session.get(self.url, headers=headers, params=params, timeout=g_timeout, auth=self.authentication) as r:
            print("google.InputStream.start() 3: %s - %s" % (r.status_code, r.headers))
            if r.status_code == requests.codes.partial_content or \
               r.status_code == requests.codes.ok:
                sequence = uno.ByteSequence(r.content)
                length = int(r.headers['Content-Length'])
                self.start += length
                print("google.InputStream.start() 4 %s" % self.start)
        print("google.InputStream.start() 5")
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
        self.start = 0


class ActiveDataSource(unohelper.Base, XActiveDataSource, XActiveDataControl):
    def __init__(self, auth, id, size):
        self.url = '%s/%s' % (g_url, id)
        self.auth = auth
        self.size = size
        self.listeners = []
        self.output = None
        self.canceled = False
        self.error = ''
    #XActiveDataSource
    def setOutputStream(self, output):
        self.output = output
    def getOutputStream(self):
        return self.output

    #XActiveDataControl
    def addListener(self, listener):
        self.listeners.append(listener)
    def removeListener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)
    def start(self):
        for listener in self.listeners:
            listener.started()
        start = 0
        chunk = min(self.size, g_chunk)
        print("google.ActiveDataSource.start()1")
        session = requests.Session()
        headers = {}
        headers['Content-Type'] = None
        headers['Accept-Encoding'] = 'gzip'
        params = {'alt': 'media'}
        while start < self.size and not self.canceled:
            end = min(start + chunk -1, self.size -1)
            headers['Range'] = 'bytes=%s-%s' % (start, end)
            print("google.ActiveDataSource.start()2: %s" % (headers['Range'], ))
            with session.get(self.url, headers=headers, params=params, timeout=g_timeout, auth=self.auth) as r:
                print("google.ActiveDataSource.start()3: %s - %s" % (r.status_code, r.headers))
                if r.status_code == requests.codes.partial_content or \
                   r.status_code == requests.codes.ok:
                    self.output.writeBytes(uno.ByteSequence(r.content))
                    start += int(r.headers['Content-Length'])
                    print("google.ActiveDataSource.start()4 %s" % start)
                else:
                    self.error = 'http error status:%s - headers:%s' % (r.status_code, r.headers)
                    break
        self.output.flush()
        self.output.closeOutput()
        for listener in self.listeners:
            if self.error:
                listener.error(Exception(self.error, self))
            if self.canceled:
                listener.terminated()
            listener.closed()
        print("google.ActiveDataSource.start()5")
    def terminate(self):
        self.canceled = True


class ActiveDataSink(unohelper.Base, XActiveDataSink, XActiveDataControl):
    def __init__(self, auth, location, size, mimetype, chunk):
        self.auth = auth
        self.location = location
        self.size = size
        self.mimetype = mimetype
        self.chunk = chunk
        self.listeners = []
        self.input = None
        self.canceled = False
        self.error = ''
    #XActiveDataSink
    def setInputStream(self, input):
        self.input = input
    def getInputStream(self):
        return self.input

    #XActiveDataControl
    def addListener(self, listener):
        self.listeners.append(listener)
    def removeListener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)
    def start(self):
        for listener in self.listeners:
            listener.started()
        print("contentlib.PyActiveDataSink.start() 1")
        start = 0
        session = requests.Session()
        headers = {}
        headers['Content-Range'] = 'bytes */%s' % self.size
        with session.put(self.location, headers=headers, timeout=g_timeout, auth=self.auth) as r:
            if r.status_code == requests.codes.ok:
                if 'Range' in r.headers:
                    start = int(r.headers['Range'].split('-')[-1]) +1
        chunk = min(self.size, self.chunk)
        headers['Content-Type'] = self.mimetype
        while start < self.size and not self.canceled:
            end = min(start + chunk -1, self.size -1)
            headers['Content-Range'] = 'bytes %s-%s/%s' % (start, end, self.size)
            print("contentlib.PyActiveDataSink.start() 2 %s" % (headers['Content-Range'], ))
            length, sequence = self.input.readBytes(None, chunk)
            data = sequence.value
            with session.put(self.location, headers=headers, data=data, auth=self.auth) as r:
                print("contentlib.PyActiveDataSink.start() 3 %s %s" % (r.status_code, r.headers))
                if r.status_code == requests.codes.ok or r.status_code == requests.codes.created:
                    start += length
                elif r.status_code == requests.codes.permanent_redirect:
                    if 'Range' in r.headers:
                        start += int(r.headers['Range'].split('-')[-1]) +1
                else:
                    self.error = 'http error status:%s - headers:%s' % (r.status_code, r.headers)
                    break
        self.input.closeInput()
        for listener in self.listeners:
            if self.error:
                listener.error(Exception(self.error, self))
            if self.canceled:
                listener.terminated()
            listener.closed()
        print("contentlib.PyActiveDataSink.start()4")
    def terminate(self):
        self.canceled = True
