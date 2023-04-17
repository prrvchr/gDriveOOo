#!
# -*- coding: utf-8 -*-

"""
╔════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                    ║
║   Copyright (c) 2020 https://prrvchr.github.io                                     ║
║                                                                                    ║
║   Permission is hereby granted, free of charge, to any person obtaining            ║
║   a copy of this software and associated documentation files (the "Software"),     ║
║   to deal in the Software without restriction, including without limitation        ║
║   the rights to use, copy, modify, merge, publish, distribute, sublicense,         ║
║   and/or sell copies of the Software, and to permit persons to whom the Software   ║
║   is furnished to do so, subject to the following conditions:                      ║
║                                                                                    ║
║   The above copyright notice and this permission notice shall be included in       ║
║   all copies or substantial portions of the Software.                              ║
║                                                                                    ║
║   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,                  ║
║   EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES                  ║
║   OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.        ║
║   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY             ║
║   CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,             ║
║   TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE       ║
║   OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                    ║
║                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════╝
"""

import uno
import unohelper

from com.sun.star.ucb.ConnectionMode import OFFLINE

from com.sun.star.rest.ParameterType import QUERY

from com.sun.star.ucb import IllegalIdentifierException

from .providerbase import ProviderBase

from .dbtool import toUnoDateTime

from .configuration import g_identifier
from .configuration import g_scheme
from .configuration import g_provider
from .configuration import g_host
from .configuration import g_url
from .configuration import g_upload
from .configuration import g_userfields
from .configuration import g_itemfields
from .configuration import g_childfields
from .configuration import g_chunk
from .configuration import g_buffer
from .configuration import g_pages
from .configuration import g_IdentifierRange
from .configuration import g_folder
from .configuration import g_office
from .configuration import g_link
from .configuration import g_doc_map

from . import ijson
import traceback


class Provider(ProviderBase):
    def __init__(self, ctx, logger):
        self._ctx = ctx
        self._logger = logger
        self.Scheme = g_scheme
        self.Link = ''
        self.Folder = ''
        self.SourceURL = ''
        self.SessionMode = OFFLINE
        self._Error = ''
        self._folders = []
        self._chunk = 64 * 1024

    @property
    def Name(self):
        return g_provider
    @property
    def Host(self):
        return g_host
    @property
    def BaseUrl(self):
        return g_url
    @property
    def UploadUrl(self):
        return g_upload
    @property
    def Office(self):
        return g_office
    @property
    def Document(self):
        return g_doc_map
    @property
    def Chunk(self):
        return g_chunk
    @property
    def Buffer(self):
        return g_buffer
    @property
    def TimeStampPattern(self):
        return '%Y-%m-%dT%H:%M:%S.00'
    @property
    def IdentifierRange(self):
        return g_IdentifierRange
    @property
    def SupportDuplicate(self):
        return True

    def getFirstPullRoots(self, user):
        return (user.RootId, )

    def getUser(self, source, request, name):
        user = {}
        user.update(self._getUser(source, request, name))
        user.update(self._getRoot(source, request, name))
        return user

    def parseNewIdentifiers(self, response):
        events = ijson.sendable_list()
        parser = ijson.parse_coro(events)
        iterator = response.iterContent(self._chunk, False)
        while iterator.hasMoreElements():
            chunk = iterator.nextElement().value
            print("Provider.parseNewIdentifiers() Content:\n%s" % chunk.decode('utf-8'))
            parser.send(chunk)
            for prefix, event, value in events:
                print("Provider.parseNewIdentifiers() Prefix: %s - Event: %s - Value: %s" % (prefix, event, value))
                if (prefix, event) == ('ids.item', 'string'):
                    yield value
            del events[:]
        parser.close()

    def parseItems(self, request, parameter):
        while parameter.hasNextPage():
            events = ijson.sendable_list()
            parser = ijson.parse_coro(events)
            response = request.execute(parameter)
            if not response.Ok:
                break
            iterator = response.iterContent(self._chunk, False)
            while iterator.hasMoreElements():
                chunk = iterator.nextElement().value
                print("Provider.parseItems() Method: %s- Page: %s - Content: \n: %s" % (parameter.Name, parameter.PageCount, chunk.decode('utf-8')))
                parser.send(chunk)
                for prefix, event, value in events:
                    #print("Provider._parseFolderContent() Prefix: %s - Event: %s - Value: %s" % (prefix, event, value))
                    if (prefix, event) == ('nextPageToken', 'string'):
                        parameter.setNextPage('pageToken', value, QUERY)
                    elif (prefix, event) == ('files.item', 'start_map'):
                        itemid = name = created = modified = mimetype = None
                        size = 0
                        addchild = canrename = True
                        trashed = readonly = versionable = False
                        parents = []
                    elif (prefix, event) == ('files.item.id', 'string'):
                        itemid = value
                    elif (prefix, event) == ('files.item.name', 'string'):
                        name = value
                    elif (prefix, event) == ('files.item.createdTime', 'string'):
                        created = self.parseDateTime(value)
                    elif (prefix, event) == ('files.item.modifiedTime', 'string'):
                        modified = self.parseDateTime(value)
                    elif (prefix, event) == ('files.item.mimeType', 'string'):
                        mimetype = value
                    elif (prefix, event) == ('files.item.trashed', 'boolean'):
                        trashed = value
                    elif (prefix, event) == ('files.item.size', 'string'):
                        size = int(value)
                    elif (prefix, event) == ('files.item.parents.item', 'string'):
                        parents.append(value)
                    elif (prefix, event) == ('files.item.capabilities.canAddChildren', 'boolean'):
                        addchild = value
                    elif (prefix, event) == ('files.item.capabilities.canRename', 'boolean'):
                        canrename = value
                    elif (prefix, event) == ('files.item.capabilities.canEdit', 'boolean'):
                        readonly = not value
                    elif (prefix, event) == ('files.item.capabilities.canReadRevisions', 'boolean'):
                        versionable = value
                    elif (prefix, event) == ('files.item', 'end_map'):
                        yield itemid, name, created, modified, mimetype, size, trashed, addchild, canrename, readonly, versionable, parents
                del events[:]
            parser.close()
            response.close()

    def parseChanges(self, request, parameter):
        while parameter.hasNextPage():
            events = ijson.sendable_list()
            parser = ijson.parse_coro(events)
            response = request.execute(parameter)
            if not response.Ok:
                break
            iterator = response.iterContent(self._chunk, False)
            while iterator.hasMoreElements():
                chunk = iterator.nextElement().value
                print("Provider.parseChanges() Method: %s- Page: %s - Content: \n: %s" % (parameter.Name, parameter.PageCount, chunk.decode('utf-8')))
                parser.send(chunk)
                for prefix, event, value in events:
                    #print("Provider._parseFolderContent() Prefix: %s - Event: %s - Value: %s" % (prefix, event, value))
                    if (prefix, event) == ('nextPageToken', 'string'):
                        parameter.setNextPage('pageToken', value, QUERY)
                    elif (prefix, event) == ('newStartPageToken', 'string'):
                        parameter.SyncToken = value
                    elif (prefix, event) == ('changes.item', 'start_map'):
                        itemid = name = modified = None
                        trashed = False
                    elif (prefix, event) == ('changes.item.removed', 'boolean'):
                        trashed = value
                    elif (prefix, event) == ('changes.item.fileId', 'string'):
                        itemid = value
                    elif (prefix, event) == ('changes.item.time', 'string'):
                        modified = self.parseDateTime(value)
                    elif (prefix, event) == ('changes.item.file.name', 'string'):
                        name = value
                    elif (prefix, event) == ('changes.item', 'end_map'):
                        yield itemid, trashed, name, modified
                del events[:]
            parser.close()
            response.close()

    def _getUser(self, source, request, name):
        parameter = self.getRequestParameter(request, 'getUser')
        response = request.execute(parameter)
        if not response.Ok:
            msg = self._logger.resolveString(403, name)
            raise IllegalIdentifierException(msg, source)
        user = self._parseUser(response)
        response.close()
        return user

    def _getRoot(self, source, request, name):
        parameter = self.getRequestParameter(request, 'getRoot')
        response = request.execute(parameter)
        if not response.Ok:
            msg = self._logger.resolveString(403, name)
            raise IllegalIdentifierException(msg, source)
        root = self._parseRoot(response)
        response.close()
        return root

    def _parseUser(self, response):
        userid = name = displayname = None
        events = ijson.sendable_list()
        parser = ijson.parse_coro(events)
        iterator = response.iterContent(self._chunk, False)
        while iterator.hasMoreElements():
            parser.send(iterator.nextElement().value)
            for prefix, event, value in events:
                if (prefix, event) == ('user.permissionId', 'string'):
                    userid = value
                elif (prefix, event) == ('user.emailAddress', 'string'):
                    name = value
                elif (prefix, event) == ('user.displayName', 'string'):
                    displayname = value
            del events[:]
        parser.close()
        return {'UserId': userid, 'UserName': name, 'DisplayName': displayname}

    def _parseRoot(self, response):
        rootid = name = created = modified = mimetype = None
        addchild = canrename = True
        trashed = readonly = versionable = False
        events = ijson.sendable_list()
        parser = ijson.parse_coro(events)
        iterator = response.iterContent(self._chunk, False)
        while iterator.hasMoreElements():
            parser.send(iterator.nextElement().value)
            for prefix, event, value in events:
                if (prefix, event) == ('id', 'string'):
                    rootid = value
                elif (prefix, event) == ('name', 'string'):
                    name = value
                elif (prefix, event) == ('createdTime', 'string'):
                    created = self.parseDateTime(value)
                elif (prefix, event) == ('modifiedTime', 'string'):
                    modified = self.parseDateTime(value)
                elif (prefix, event) == ('mimeType', 'string'):
                    mimetype = value
                elif (prefix, event) == ('trashed', 'boolean'):
                    trashed = value
                elif (prefix, event) == ('capabilities.canAddChildren', 'boolean'):
                    addchild = value
                elif (prefix, event) == ('capabilities.canRename', 'boolean'):
                    canrename = value
                elif (prefix, event) == ('capabilities.canEdit', 'boolean'):
                    readonly = not value
                elif (prefix, event) == ('capabilities.canReadRevisions', 'boolean'):
                    versionable = value
            del events[:]
        parser.close()
        return {'RootId': rootid, 'Title': name, 'DateCreated': created, 'DateModified': modified, 
                "MediaType": mimetype, 'Trashed': trashed, 'CanAddChild': addchild, 
                'CanRename': canrename, 'IsReadOnly': readonly, 'IsVersionable': versionable}




    def parseItemId(self, response):
        return self._parseItemId(response)

    def _parseItemId(self, response):
        itemid = None
        events = ijson.sendable_list()
        parser = ijson.items_coro(events, 'id')
        iterator = response.iterContent(self._chunk, False)
        while iterator.hasMoreElements():
            parser.send(iterator.nextElement().value)
            for prefix, event, value in events:
                if (prefix, event) == ('id', 'string'):
                    itemid = value
                    break
            del events[:]
        parser.close()
        return itemid

    def parseUserToken(self, response):
        token = None
        events = ijson.sendable_list()
        parser = ijson.parse_coro(events)
        iterator = response.iterContent(self._chunk, False)
        while iterator.hasMoreElements():
            parser.send(iterator.nextElement().value)
            for prefix, event, value in events:
                if (prefix, event) == ('startPageToken', 'string'):
                    token = value
            del events[:]
        parser.close()
        return token


    def getRequestParameter(self, request, method, data=None):
        parameter = request.getRequestParameter(method)
        if method == 'getUser':
            parameter.Url = '%s/about' % self.BaseUrl
            parameter.Query = '{"fields": "%s"}' % g_userfields
        elif method == 'getRoot' :
            parameter.Url = '%s/files/root' % self.BaseUrl
            parameter.Query = '{"fields": "%s"}' % g_itemfields
        elif method == 'getFolderContent':
            parameter.Url = '%s/files' % self.BaseUrl
            query = ['"fields": "%s"' % g_childfields]
            query += ['"pageSize": "%s"' % g_pages]
            parents = "'%s' in parents" % data
            query += ['"q": "%s"' % parents]
            parameter.Query = '{%s}' % ','.join(query)
        elif method == 'getFirstPull':
            parameter.Url = '%s/files' % self.BaseUrl
            query = ['"orderBy": "folder,createdTime"']
            query += ['"fields": "%s"' % g_childfields]
            query += ['"pageSize": "%s"' % g_pages]
            parameter.Query = '{%s}' % ','.join(query)
        elif method == 'getNewIdentifier':
            parameter.Url = '%s/files/generateIds' % self.BaseUrl
            parameter.Query = '{"count": "%s", "space": "drive"}' % max(g_IdentifierRange)

        elif method == 'getItem':
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.get('Id'))
            parameter.Query = '{"fields": "%s"}' % g_itemfields
        elif method == 'getToken':
            parameter.Url = '%s/changes/startPageToken' % self.BaseUrl
        elif method == 'getPull':
            parameter.Url = '%s/changes' % self.BaseUrl
            parameter.Query = '{"pageToken": %s}' % data.Token
            #token.SyncField = 'newStartPageToken'

        elif method == 'getDocumentContent':
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.Id)
            if data.MediaType in g_doc_map:
                parameter.Url += '/export'
                parameter.Query = '{"mimeType": "%s"}' % data.MediaType
            else:
                parameter.Query = '{"alt": "media"}'
        elif method == 'updateTitle':
            parameter.Method = 'PATCH'
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.get('Id'))
            parameter.Json = '{"name": "%s"}' % data.get('Title')
        elif method == 'updateTrashed':
            parameter.Method = 'PATCH'
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.get('Id'))
            parameter.Json = '{"trashed": true}'
        elif method == 'updateParents':
            parameter.Method = 'PATCH'
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.get('Id'))
            toadd = data.get('ParentToAdd')
            toremove = data.get('ParentToRemove')
            if len(toadd) > 0:
                parameter.Json = '{"addParents": %s}' % ','.join(toadd)
            if len(toremove) > 0:
                parameter.Json = '{"removeParents": %s}' % ','.join(toremove)
        elif method == 'createNewFolder':
            parameter.Method = 'POST'
            parameter.Url = '%s/files' % self.BaseUrl
            parameter.Json = '{"id": "%s", "parents": ["%s"], "name": "%s", "mimeType": "%s"}' % \
                                (data.get('Id'), data.get('ParentId'),
                                 data.get('Title'), data.get('MediaType'))
        elif method == 'getUploadLocation':
            parameter.Method = 'PATCH'
            parameter.Url = '%s/%s' % (self.UploadUrl, data.get('Id'))
            parameter.Query = '{"uploadType": "resumable"}'
            parameter.Headers = '{"X-Upload-Content-Type": "%s"}' % data.get('MediaType')
        elif method == 'getNewUploadLocation':
            parameter.Method = 'POST'
            parameter.Url = self.UploadUrl
            parameter.Query = '{"uploadType": "resumable"}'
            parameter.Json = '{"id": "%s", "parents": ["%s"], "name": "%s", "mimeType": "%s"}' % \
                                (data.get('Id'), data.get('ParentId'),
                                 data.get('Title'), data.get('MediaType'))
            parameter.Headers = '{"X-Upload-Content-Type": "%s"}' % data.get('MediaType')
        elif method == 'getUploadStream':
            parameter.Method = 'PUT'
            parameter.Url = data.getHeader('Location')
        return parameter

    def initUser(self, database, user):
        token = self.getUserToken(user)
        if database.updateToken(user.Id, token):
            user.setToken(token)

