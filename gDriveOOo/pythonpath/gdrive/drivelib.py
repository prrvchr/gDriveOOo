#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.io import XOutputStream
from com.sun.star.io import XInputStream
from com.sun.star.io import IOException

from .drivetools import unparseDateTime
from .drivetools import g_childfields
from .drivetools import g_chunk
from .drivetools import g_length
from .drivetools import g_pages
from .drivetools import g_timeout
from .drivetools import g_url


class IdGenerator():
    def __init__(self, session, count, space='drive'):
        print("google.IdGenerator.__init__()")
        self.ids = []
        url = '%sfiles/generateIds' % g_url
        params = {'count': count, 'space': space}
        with session.get(url, params=params, timeout=g_timeout) as r:
            print("google.IdGenerator(): %s" % r.json())
            if r.status_code == session.codes.ok:
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
        if r.status_code == self.session.codes.ok:
            rows = r.json().get('files', [])
            token = r.json().get('nextPageToken', None)
        return rows, token


class InputStream(unohelper.Base, XInputStream):
    def __init__(self, session, id, size, mimetype):
        self.session = session
        self.length = 32768
        url = '%sfiles/%s/export' % (g_url, id) if mimetype else '%sfiles/%s' % (g_url, id)
        params = {'mimeType': mimetype} if mimetype else {'alt': 'media'}
        self.chunks = (s for c in Downloader(self.session, url, params, size) for s in c)
        self.buffers = b''
        print("google.InputStream.__init__()")

    #XInputStream
    def readBytes(self, sequence, length):
        available = length - len(self.buffers)
        if available < 0:
            i = abs(available)
            sequence = uno.ByteSequence(self.buffers[:i])
            self.buffers = self.buffers[i:]
        else:
            sequence = uno.ByteSequence(self.buffers)
            self.buffers = b''
            while available > 0:
                chunk = next(self.chunks, b'')
                if not chunk:
                    break
                elif len(chunk) > available:
                    sequence += chunk[:available]
                    self.buffers = chunk[available:]
                    break
                sequence += chunk
                available = length - len(sequence)
        return len(sequence), sequence
    def readSomeBytes(self, sequence, length):
        return self.readBytes(sequence, length)
    def skipBytes(self, length):
        pass
    def available(self):
        return g_chunk
    def closeInput(self):
        self.session.headers.pop('Range', None)
        self.session.close()


class Downloader():
    def __init__(self, session, url, params, size):
        print("google.ChunkDownloader.__init__()")
        self.session = session
        self.url = url
        self.size = size
        self.start = 0
        self.closed = False
        self.chunked = size > g_chunk
        self.params = params 
        print("google.ChunkDownloader.__init__()")
    def __iter__(self):
        return self
    def __next__(self):
        if self.closed:
            raise StopIteration
        print("google.ChunkDownloader.__next__() 1")
        if self.chunked:
            end = min(self.start + g_chunk, self.size)
            self.session.headers.update({'Range': 'bytes=%s-%s' % (self.start, end -1)})
        print("google.ChunkDownloader.__next__() 2: %s" % (self.session.headers, ))
        # We cannot use a 'Context Manager' here... iterator needs access to the response...
        r = self.session.get(self.url, params=self.params, timeout=g_timeout, stream=True)
        print("google.ChunkDownloader.__next__() 3: %s - %s" % (r.status_code, r.headers))
        if r.status_code == self.session.codes.partial_content:
            if self.chunked:
                self.start = end
                self.closed = self.start == self.size
            else:
                self.start += int(r.headers.get('Content-Length', 0))
            print("google.ChunkDownloader.__next__() 4 %s - %s" % (self.closed, self.start))
        elif  r.status_code == self.session.codes.ok:
            self.closed = True
            print("google.ChunkDownloader.__next__() 5 %s - %s" % (self.closed, self.start))
        else:
            # Without 'Context Manager', to release the connection back to the pool,
            # because we don't have consumed all the data, we need to close the response
            r.close()
            self.closed = True
            raise IOException('Error Downloading file...', self)
        return r.iter_content(g_length)
    # for python v2.xx
    def next(self):
        return self.__next__()


class OutputStream(unohelper.Base, XOutputStream):
    def __init__(self, session, url, size):
        self.session = session
        self.url = url
        self.size = size
        self.buffers = []
        self.length = 0
        self.start = 0
        self.closed = False
        self.chunked = size > g_chunk
    # XOutputStream
    def writeBytes(self, sequence):
        if self.closed:
            raise IOException('OutputStream is closed...', self)
        self.buffers.append(sequence.value)
        self.length += len(sequence)
        if self._flushable() and not self._flush():
            raise IOException('Error Uploading file...', self)
        else:
            print("gdrive.OutputStream.writeBytes() Bufferize: %s - %s" % (self.start, self.length))
    def flush(self):
        print("gdrive.OutputStream.flush()")
        if self.closed:
            raise IOException('OutputStream is closed...', self)
        if self._flushable(True) and not self._flush():
            raise IOException('Error Uploading file...', self)
    def closeOutput(self):
        print("gdrive.OutputStream.closeOutput() 1")
        if not self.closed:
            self._close()
        print("gdrive.OutputStream.closeOutput() 2")
    def _flushable(self, last=False):
        if last:
            return self.length > 0
        elif self.chunked:
            return self.length >= g_chunk
        return False
    def _flush(self):
        print("gdrive.OutputStream._write() 1: %s" % (self.start, ))
        end = self.start + self.length -1
        if self.chunked:
            self.session.headers.update({'Content-Range': 'bytes %s-%s/%s' % (self.start, end, self.size)})
        print("gdrive.OutputStream._write() 2: %s" % (self.session.headers, ))
        with self.session.put(self.url, data=iter(self.buffers)) as r:
            print("gdrive.OutputStream._write() 3: %s" % (r.request.headers, ))
            print("gdrive.OutputStream._write() 4: %s - %s" % (r.status_code, r.headers))
            print("gdrive.OutputStream._write() 5: %s" % (r.json(), ))
            if r.status_code == self.session.codes.ok:
                print("gdrive.OutputStream._write() 6")
                self.start = end
                self.buffers = []
                self.length = 0
                return True
            elif r.status_code == self.session.codes.created:
                print("gdrive.OutputStream._write() 7")
                self.start = end
                print("gdrive.OutputStream._write() 8")
                self.buffers = []
                self.length = 0
                print("gdrive.OutputStream._write() 9 %s" % id)
                return True
            elif r.status_code == self.session.codes.permanent_redirect:
                print("gdrive.OutputStream._write() 10")
                if 'Range' in r.headers:
                    self.start += int(r.headers['Range'].split('-')[-1]) +1
                    self.buffers = []
                    self.length = 0
                    return True
            else:
                print("gdrive.OutputStream._write() 11 %s" % r.text)
        return False
    def _close(self):
        print("gdrive.OutputStream._close() 1")
        self.flush()
        print("gdrive.OutputStream._close() 2: %s" % (self.session.headers, ))
        self.session.headers.pop('Content-Range', None)
        self.session.close()
        self.closed = True
        print("gdrive.OutputStream._close() 3: %s" % (self.session.headers, ))
