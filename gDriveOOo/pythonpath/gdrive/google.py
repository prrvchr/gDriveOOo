#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.io import XActiveDataSource, XActiveDataSink, XActiveDataControl, XInputStream

import requests
import sys

if sys.version_info[0] < 3:
    requests.packages.urllib3.disable_warnings()

g_url = 'https://www.googleapis.com/drive/v3/files'
g_itemfields = 'id,parents,name,mimeType,size,createdTime,modifiedTime,capabilities(canEdit,canRename,canAddChildren)'
g_childfields = 'kind,nextPageToken,files(%s)' % g_itemfields
g_chunk = 262144
g_pages = 100


def getItem(authentication, id):
    result = {}
    timeout = 10
    url = '%s/%s' % (g_url, id)
    params = {}
    params['fields'] = g_itemfields
    with requests.get(url, params=params, timeout=timeout, auth=authentication) as r:
        print("google.getItem(): %s" % r.json())
        if r.status_code == requests.codes.ok:
            result = r.json()
    return result


class ChildGenerator():
    def __init__(self, authentication, id, timeout=15):
        print("google.ChildGenerator.__init__()")
        self.authentication = authentication
        self.params = {'fields': g_childfields, 'pageSize': g_pages}
        self.params['q'] = "'%s' in parents" % id
        self.timeout = timeout
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
        with self.session.get(g_url, params=self.params, timeout=self.timeout, auth=self.authentication) as r:
            print("google.ChildGenerator(): %s" % r.json())
            if r.status_code == requests.codes.ok:
                result = r.json()
                if 'files' in result:
                    rows = result['files']
                if 'nextPageToken' in result:
                    token = result['nextPageToken']
        return rows, token


class InputStream(unohelper.Base, XInputStream):
    def __init__(self, auth, id, size, timeout=15):
        self.auth = auth
        self.url = '%s/%s' % (g_url, id)
        self.size = size
        self.start = 0
        self.timeout = timeout
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
        with self.session.get(self.url, headers=headers, params=params, timeout=self.timeout, auth=self.auth) as r:
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
            with session.get(self.url, headers=headers, params=params, auth=self.auth) as r:
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
        with session.put(self.location, headers=headers, auth=self.auth) as r:
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
