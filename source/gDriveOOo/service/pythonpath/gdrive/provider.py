#!
# -*- coding: utf-8 -*-

"""
╔════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                    ║
║   Copyright (c) 2020-25 https://prrvchr.github.io                                  ║
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
from .ucp import g_ucboffice

from .dbtool import currentDateTimeInTZ
from .dbtool import currentUnoDateTime


from .configuration import g_identifier
from .configuration import g_scheme
from .configuration import g_provider
from .configuration import g_host
from .configuration import g_url
from .configuration import g_upload
from .configuration import g_ucpfolder
from .configuration import g_userfields
from .configuration import g_itemfields
from .configuration import g_childfields
from .configuration import g_chunk
from .configuration import g_pages
from .configuration import g_IdentifierRange
from .configuration import g_doc_map

import ijson
import traceback


class Provider(ProviderBase):

    # Must be implemented properties
    @property
    def BaseUrl(self):
        return g_url
    @property
    def Host(self):
        return g_host
    @property
    def Name(self):
        return g_provider
    @property
    def UploadUrl(self):
        return g_upload

    # Must be implemented method
    def getDocumentLocation(self, user, item):
        # XXX: Nothing to do here
        return item

    def getFirstPullRoots(self, user):
        return (user.RootId, )

    def getUser(self, source, request, name):
        user = self._getUser(source, request)
        user.update(self._getRoot(source, request))
        return user

    def mergeNewFolder(self, user, oldid, response):
        # XXX: Nothing to merge: we already have the final ItemId
        response.close()
        return oldid

    def parseFolder(self, user, data, parameter):
        return self.parseItems(user.Request, parameter, user.RootId)

    def parseItems(self, request, parameter, parentid):
        # XXX: link and path are not used here...
        link = ''
        path = None
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
                            parents = (parentid, )
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
                        elif (prefix, event) == ('files.item.parents', 'start_array'):
                            parents = []
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
                                yield {'Id': itemid,
                                       'Name': name,
                                       'DateCreated': created,
                                       'DateModified': modified,
                                       'MediaType': mimetype,
                                       'Size': size,
                                       'Link': link,
                                       'Trashed': trashed,
                                       'CanAddChild': addchild,
                                       'CanRename': canrename,
                                       'IsReadOnly': readonly,
                                       'IsVersionable': versionable,
                                       'Parents': parents,
                                       'Path': path}
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

    def parseUploadLocation(self, response):
        url = None
        if response.hasHeader('Location'):
            url = response.getHeader('Location')
        response.close()
        return url

    def parseUserToken(self, response):
        token = response.getJson().getString('startPageToken')
        return token

    def updateItemId(self, user, oldid, response):
        # XXX: Google drive API already provides the definitive identifiers,
        # XXX: there is nothing to do here, just close the response...
        response.close()
        return oldid

    # Can be rewrited properties
    @property
    def IdentifierRange(self):
        return g_IdentifierRange

    # Can be rewrited method
    def initSharedDocuments(self, user, reset, datetime):
        count = download = 0
        folder = {'Id':            user.ShareId,
                  'Name':          self.SharedFolderName,
                  'DateCreated':   user.DateCreated,
                  'DateModified':  user.DateModified,
                  'MediaType':     g_ucpfolder,
                  'Size':          0,
                  'Link':          '',
                  'Trashed':       False,
                  'CanAddChild':   False,
                  'CanRename':     False,
                  'IsReadOnly':    False,
                  'IsVersionable': False,
                  'Parents':       (user.RootId),
                  'Path':          None}
        user.DataBase.mergeItem(user.Id, user.RootId, datetime, folder, -1)
        parameter = self.getRequestParameter(user.Request, 'getSharedFolderContent')
        items = self.parseItems(user.Request, parameter, user.ShareId)
        for item in user.DataBase.mergeItems(user.Id, user.ShareId, datetime, items, -1):
            count += 1
            if reset:
                download += self.pullFileContent(user, item)
        return count, download, parameter.PageCount

    def initUser(self, user, token):
        token = self.getUserToken(user)
        super().initUser(user, token)

    def pullUser(self, user):
        count = download = 0
        timestamp = currentDateTimeInTZ()
        parameter = self.getRequestParameter(user.Request, 'getChanges', user.Token)
        for itemid in self._parseChanges(user.Request, parameter):
            item = self._pullItem(user, itemid, timestamp)
            count += 1
            if item is not None:
                download += self.pullFileContent(user, item)
        return count, download, parameter.PageCount, parameter.SyncToken

    # Private method
    def _getUser(self, source, request):
        parameter = self.getRequestParameter(request, 'getUser')
        response = request.execute(parameter)
        if not response.Ok:
            self.raiseIllegalIdentifierException(source, 561, parameter, response)
        user = self._parseUser(response)
        response.close()
        return user

    def _getRoot(self, source, request):
        parameter = self.getRequestParameter(request, 'getItem', 'root')
        response = request.execute(parameter)
        if response.Ok:
            item = self._parseItem(response)
            user = {'RootId':       item.get('Id'),
                    'DateCreated':  item.get('DateCreated'),
                    'DateModified': item.get('DateModified')}
        # FIXME: If we use scope drive.file we have a 404 error
        # FIXME: see: https://issuetracker.google.com/issues/377531203
        elif response.StatusCode == 404:
            try:
                msg = response.getJson().getStructure('error').getString('message')
                rootid = msg.split()[-1][:-1]
                datetime = currentUnoDateTime()
                user = {'RootId':       rootid,
                        'DateCreated':  datetime,
                        'DateModified': datetime}
            except:
                self.raiseIllegalIdentifierException(source, 571, parameter, response)
        else:
            self.raiseIllegalIdentifierException(source, 571, parameter, response)
        response.close()
        return user

    def _parseChanges(self, request, parameter):
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
                        elif (prefix, event) == ('newStartPageToken', 'string'):
                            parameter.SyncToken = value
                        elif (prefix, event) == ('changes.item.fileId', 'string'):
                            yield value
                    del events[:]
                parser.close()
            response.close()

    def _parseItem(self, response, parentid=None):
        timestamp = currentUnoDateTime()
        itemid = name = mimetype = None
        created = modified = timestamp
        size = 0
        addchild = canrename = True
        trashed = readonly = versionable = False
        parents = () if parentid is None else (parentid, )
        # XXX: link and path are not used here...
        link = ''
        path = None
        events = ijson.sendable_list()
        parser = ijson.parse_coro(events)
        iterator = response.iterContent(g_chunk, False)
        while iterator.hasMoreElements():
            parser.send(iterator.nextElement().value)
            for prefix, event, value in events:
                if (prefix, event) == ('id', 'string'):
                    itemid = value
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
                elif (prefix, event) == ('size', 'string'):
                    size = int(value)
                elif (prefix, event) == ('parents', 'start_array'):
                    parents = []
                elif (prefix, event) == ('parents.item', 'string'):
                    parents.append(value)
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
        return {'Id': itemid,
                'Name': name,
                'DateCreated': created,
                'DateModified': modified,
                'MediaType': mimetype,
                'Size': size,
                'Link': link,
                'Trashed': trashed,
                'CanAddChild': addchild,
                'CanRename': canrename,
                'IsReadOnly': readonly,
                'IsVersionable': versionable,
                'Parents': parents,
                'Path': path}

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
        return {'Id': userid, 'Name': name, 'DisplayName': displayname}

    def _pullItem(self, user, itemid, datetime):
        item = None
        parameter = self.getRequestParameter(user.Request, 'getItem', itemid)
        response = user.Request.execute(parameter)
        if response.Ok:
            item = self._parseItem(response, user.RootId)
            user.DataBase.mergeItem(user.Id, user.RootId, datetime, item)
        response.close()
        return item

    # Requests get Parameter method
    def getRequestParameter(self, request, method, data=None):
        parameter = request.getRequestParameter(method)
        parameter.Url = self.BaseUrl

        if method == 'getUser':
            parameter.Url += '/about'
            parameter.setQuery('fields', g_userfields)

        elif method == 'getFolderContent':
            parameter.Url += '/files'
            parameter.setQuery('orderBy', 'folder,createdTime')
            parameter.setQuery('fields', g_childfields)
            parameter.setQuery('pageSize', g_pages)
            parameter.setQuery('q', "'%s' in parents" % data.get('Id'))

        elif method == 'getSharedFolderContent':
            parameter.Url += '/files'
            parameter.setQuery('orderBy', 'folder,createdTime')
            parameter.setQuery('fields', g_childfields)
            parameter.setQuery('pageSize', g_pages)
            parameter.setQuery('q', "sharedWithMe=true")

        elif method == 'getFirstPull':
            parameter.Url += '/files'
            parameter.setQuery('orderBy', 'folder,createdTime')
            parameter.setQuery('fields', g_childfields)
            parameter.setQuery('pageSize', g_pages)
            # FIXME: We don't want to see files shared with me, so we need this query
            parameter.setQuery('q', "'me' in owners")

        elif method == 'getNewIdentifier':
            parameter.Url += '/files/generateIds'
            parameter.setQuery('count', str(max(g_IdentifierRange)))
            parameter.setQuery('space', 'drive')

        elif method == 'getItem':
            parameter.Url += '/files/' + data
            parameter.setQuery('fields', g_itemfields)

        elif method == 'getToken':
            parameter.Url += '/changes/startPageToken'
            parameter.setQuery('supportsAllDrives', True)

        elif method == 'getChanges':
            parameter.Url += '/changes'
            parameter.setQuery('pageSize', g_pages)
            parameter.setQuery('pageToken', data)

        elif method == 'downloadFile':
            parameter.Url += '/files/' + data.get('Id')
            mediatype = data.get('MediaType')
            if mediatype in g_doc_map:
                parameter.Url += '/export'
                parameter.setQuery('mimeType', g_doc_map.get(mediatype))
            else:
                parameter.setQuery('alt', 'media')

        elif method == 'updateName':
            parameter.Method = 'PATCH'
            parameter.Url += '/files/' + data.get('Id')
            parameter.setJson('name',  data.get('Name'))

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
            parameter.setJson('name', data.get('Name'))
            parameter.setJson('mimeType', data.get('MediaType'))

        elif method == 'getUploadLocation':
            parameter.Method = 'PATCH'
            parameter.Url = self.UploadUrl + '/' + data.get('Id')
            parameter.setQuery('uploadType', 'resumable')

        elif method == 'getNewUploadLocation':
            parameter.Method = 'POST'
            parameter.Url = self.UploadUrl
            parameter.setHeader('X-Upload-Content-Type', data.get('MediaType'))
            parameter.setQuery('uploadType', 'resumable')
            parameter.setJson('id', data.get('Id'))
            parameter.setJson('parents', [data.get('ParentId')])
            parameter.setJson('name', data.get('Name'))
            parameter.setJson('mimeType', data.get('MediaType'))

        elif method == 'getUploadStream':
            parameter.Method = 'PUT'
            parameter.Url = data
            parameter.setUpload(PERMANENT_REDIRECT, 'Range', '-([0-9]+)', 1, HEADER)

        return parameter

