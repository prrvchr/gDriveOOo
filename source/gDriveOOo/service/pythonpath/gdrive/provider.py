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

from com.sun.star.rest.HTTPStatusCode import PERMANENT_REDIRECT

from com.sun.star.rest.ParameterType import HEADER
from com.sun.star.rest.ParameterType import QUERY

from com.sun.star.ucb import IllegalIdentifierException

from .ucp import Provider as ProviderBase

from .dbtool import currentDateTimeInTZ
from .dbtool import currentUnoDateTime

from .unotool import generateUuid

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
from .configuration import g_pages
from .configuration import g_IdentifierRange
from .configuration import g_folder
from .configuration import g_office
from .configuration import g_link
from .configuration import g_doc_map

import ijson
import traceback


class Provider(ProviderBase):

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
    def DateTimeFormat(self):
        return '%Y-%m-%dT%H:%M:%S.%fZ'
    @property
    def Folder(self):
        return self._folder
    @property
    def Link(self):
        return self._link

    @property
    def IdentifierRange(self):
        return g_IdentifierRange
    @property
    def SupportDuplicate(self):
        return True

    def getFirstPullRoots(self, user):
        return (user.RootId, )

    def initUser(self, database, user, token):
        token = self.getUserToken(user)
        if database.updateToken(user.Id, token):
            user.setToken(token)

    def getUser(self, source, request, name):
        user = self._getUser(source, request, name)
        root = self._getRoot(source, request, name)
        return user, root

    def initSharedDocuments(self, user, datetime):
        itemid = generateUuid()
        timestamp = currentUnoDateTime()
        user.DataBase.createSharedFolder(user, itemid, self.SharedFolderName, g_folder, datetime, timestamp)
        parameter = self.getRequestParameter(user.Request, 'getSharedFolderContent')
        iterator = self._parseSharedFolder(user.Request, parameter, itemid, timestamp)
        user.DataBase.pullItems(iterator, user.Id, datetime, 0)

    def _parseSharedFolder(self, request, parameter, itemid, timestamp):
        parents = [itemid, ]
        addchild = True
        trashed = readonly = versionable = False
        mimetype = g_folder
        size = 0
        link = path = ''
        while parameter.hasNextPage():
            response = request.execute(parameter)
            if response.Ok:
                events = ijson.sendable_list()
                parser = ijson.parse_coro(events)
                iterator = response.iterContent(g_chunk, False)
                while iterator.hasMoreElements():
                    parser.send(iterator.nextElement().value)
                    for prefix, event, value in events:
                        if (prefix, event) == ('nextPageToken', 'string'):
                            parameter.setNextPage('pageToken', value, QUERY)
                        elif (prefix, event) == ('drives.item', 'start_map'):
                            itemid = name = None
                            created = modified = timestamp
                            rename = False
                        elif (prefix, event) == ('drives.item.id', 'string'):
                            itemid = value
                        elif (prefix, event) == ('drives.item.name', 'string'):
                            name = value
                        elif (prefix, event) == ('drives.item.createdTime', 'string'):
                            created = modified = self.parseDateTime(value)
                        elif (prefix, event) == ('drives.item.capabilities.canRenameDrive', 'boolean'):
                            rename = value
                        elif (prefix, event) == ('value.item', 'end_map'):
                            if itemid and name:
                                yield itemid, name, created, modified, mimetype, size, link, trashed, addchild, rename, readonly, versionable, path, parents
                    del events[:]
                parser.close()
            response.close()


    def parseUploadLocation(self, response):
        url = None
        if response.hasHeader('Location'):
            url = response.getHeader('Location')
        response.close()
        return url

    def updateItemId(self, database, oldid, response):
        # TODO: Google drive API already provides the definitive identifiers,
        # TODO: there is nothing to do here, just close the response...
        response.close()
        return oldid

    def getDocumentLocation(self, content):
        # FIXME: This method being also called by the replicator,
        # FIXME: we must provide a dictionary
        return content.MetaData

    def mergeNewFolder(self, user, oldid, response):
        # FIXME: Nothing to merge: we already have the final ItemId
        if response:
            response.close()
        return oldid

    def parseRootFolder(self, parameter, content):
        return self.parseItems(content.User.Request, parameter)

    def parseItems(self, request, parameter):
        link = path = ''
        timestamp = currentUnoDateTime()
        while parameter.hasNextPage():
            response = request.execute(parameter)
            if response.Ok:
                events = ijson.sendable_list()
                parser = ijson.parse_coro(events)
                iterator = response.iterContent(g_chunk, False)
                while iterator.hasMoreElements():
                    parser.send(iterator.nextElement().value)
                    for prefix, event, value in events:
                        if (prefix, event) == ('nextPageToken', 'string'):
                            parameter.setNextPage('pageToken', value, QUERY)
                        elif (prefix, event) == ('files.item', 'start_map'):
                            itemid = name = mimetype = None
                            created = modified = timestamp
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
                            if itemid and name and mimetype:
                                yield itemid, name, created, modified, mimetype, size, link, trashed, addchild, canrename, readonly, versionable, path, parents
                    del events[:]
                parser.close()
            response.close()

    def parseChanges(self, request, parameter):
        while parameter.hasNextPage():
            response = request.execute(parameter)
            if not response.Ok:
                break
            events = ijson.sendable_list()
            parser = ijson.parse_coro(events)
            iterator = response.iterContent(g_chunk, False)
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

    def parseNewIdentifiers(self, response):
        events = ijson.sendable_list()
        parser = ijson.parse_coro(events)
        iterator = response.iterContent(g_chunk, False)
        while iterator.hasMoreElements():
            parser.send(iterator.nextElement().value)
            for prefix, event, value in events:
                if (prefix, event) == ('ids.item', 'string'):
                    yield value
            del events[:]
        parser.close()

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
        iterator = response.iterContent(g_chunk, False)
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
        return userid, name, displayname

    def _parseRoot(self, response):
        rootid = name = created = modified = mimetype = None
        addchild = canrename = True
        trashed = readonly = versionable = False
        events = ijson.sendable_list()
        parser = ijson.parse_coro(events)
        iterator = response.iterContent(g_chunk, False)
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
        return rootid, name, created, modified, mimetype, trashed, addchild, canrename, readonly, versionable

    def parseItemId(self, response):
        return self._parseItemId(response)

    def _parseItemId(self, response):
        itemid = None
        events = ijson.sendable_list()
        parser = ijson.items_coro(events, 'id')
        iterator = response.iterContent(g_chunk, False)
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
        iterator = response.iterContent(g_chunk, False)
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
        parameter.Url = self.BaseUrl
        if method == 'getUser':
            parameter.Url += '/about'
            parameter.setQuery('fields', g_userfields)

        elif method == 'getRoot' :
            parameter.Url += '/files/root'
            parameter.setQuery('fields', g_itemfields)

        elif method == 'getSharedFolderContent':
            parameter.Url += '/drives'

        elif method == 'getFolderContent':
            parameter.Url += '/files'
            parameter.setQuery('fields', g_childfields)
            parameter.setQuery('pageSize', g_pages)
            parameter.setQuery('q', "'%s' in parents" % data.Id)

        elif method == 'getFirstPull':
            parameter.Url += '/files'
            parameter.setQuery('orderBy', 'folder,createdTime')
            parameter.setQuery('fields', g_childfields)
            parameter.setQuery('pageSize', g_pages)

        elif method == 'getNewIdentifier':
            parameter.Url += '/files/generateIds'
            parameter.setQuery('count', str(max(g_IdentifierRange)))
            parameter.setQuery('space', 'drive')

        elif method == 'getItem':
            parameter.Url += '/files/' + data.get('Id')
            parameter.setQuery('fields', g_itemfields)

        elif method == 'getToken':
            parameter.Url += '/changes/startPageToken'

        elif method == 'getPull':
            parameter.Url += '/changes'
            parameter.setQuery('pageToken', data.Token)
            #token.SyncField = 'newStartPageToken'

        elif method == 'getDocumentContent':
            parameter.Url += '/files/' + data.get('Id')
            if data.get('MediaType') in g_doc_map:
                parameter.Url += '/export'
                parameter.setQuery('mimeType', data.get('MediaType'))
            else:
                parameter.setQuery('alt', 'media')

        elif method == 'updateTitle':
            parameter.Method = 'PATCH'
            parameter.Url += '/files/' + data.get('Id')
            parameter.setJson('name',  data.get('Title'))

        elif method == 'updateTrashed':
            parameter.Method = 'PATCH'
            parameter.Url += '/files/' + data.get('Id')
            parameter.setJson('trashed', True)

        elif method == 'updateParents':
            parameter.Method = 'PATCH'
            parameter.Url += '/files/' + data.get('Id')
            toadd = data.get('ParentToAdd')
            toremove = data.get('ParentToRemove')
            if len(toadd) > 0:
                parameter.setJson('addParents', ','.join(toadd))
            if len(toremove) > 0:
                parameter.setJson('removeParents', ','.join(toremove))

        elif method == 'createNewFolder':
            parameter.Method = 'POST'
            parameter.Url += '/files'
            parameter.setJson('id', data.get('Id'))
            parameter.setJson('parents', [data.get('ParentId')])
            parameter.setJson('name', data.get('Title'))
            parameter.setJson('mimeType', data.get('MediaType'))

        elif method == 'getUploadLocation':
            parameter.Method = 'PATCH'
            parameter.Url = self.UploadUrl + '/' + data.get('Id')
            parameter.setQuery('uploadType', 'resumable')

        elif method == 'getNewUploadLocation':
            parameter.Method = 'POST'
            parameter.Url = self.UploadUrl
            parameter.setQuery('uploadType', 'resumable')
            parameter.setJson('id', data.get('Id'))
            parameter.setJson('parents', [data.get('ParentId')])
            parameter.setJson('name', data.get('Title'))
            parameter.setJson('mimeType', data.get('MediaType'))
            parameter.setHeader('X-Upload-Content-Type', data.get('MediaType'))

        elif method == 'getUploadStream':
            parameter.Method = 'PUT'
            parameter.Url = data
            parameter.setUpload(PERMANENT_REDIRECT, 'Range', '-([0-9]+)', 1, HEADER)

        return parameter

