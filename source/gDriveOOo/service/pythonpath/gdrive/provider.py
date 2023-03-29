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

from com.sun.star.auth.RestRequestTokenType import TOKEN_NONE
from com.sun.star.auth.RestRequestTokenType import TOKEN_URL
from com.sun.star.auth.RestRequestTokenType import TOKEN_REDIRECT
from com.sun.star.auth.RestRequestTokenType import TOKEN_QUERY
from com.sun.star.auth.RestRequestTokenType import TOKEN_JSON
from com.sun.star.auth.RestRequestTokenType import TOKEN_SYNC

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

import traceback


class Provider(ProviderBase):
    def __init__(self, ctx):
        self._ctx = ctx
        self.Scheme = g_scheme
        self.Link = ''
        self.Folder = ''
        self.SourceURL = ''
        self.SessionMode = OFFLINE
        self._Error = ''
        self._folders = []

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

    def getRequestParameter(self, method, data=None):
        parameter = uno.createUnoStruct('com.sun.star.auth.RestRequestParameter')
        parameter.Name = method
        if method == 'getNewIdentifier':
            parameter.Method = 'GET'
            parameter.Url = '%s/files/generateIds' % self.BaseUrl
            parameter.Query = '{"count": "%s", "space": "drive"}' % max(g_IdentifierRange)
            token = uno.createUnoStruct('com.sun.star.auth.RestRequestToken')
            token.Type = TOKEN_NONE
            enumerator = uno.createUnoStruct('com.sun.star.auth.RestRequestEnumerator')
            enumerator.Field = 'ids'
            enumerator.Token = token
            parameter.Enumerator = enumerator
        elif method == 'getUser':
            parameter.Method = 'GET'
            parameter.Url = '%s/about' % self.BaseUrl
            parameter.Query = '{"fields": "%s"}' % g_userfields
        elif method == 'getItem':
            parameter.Method = 'GET'
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.getValue('Id'))
            parameter.Query = '{"fields": "%s"}' % g_itemfields
        elif method == 'getRoot' :
            parameter.Method = 'GET'
            parameter.Url = '%s/files/root' % self.BaseUrl
            parameter.Query = '{"fields": "%s"}' % g_itemfields
        elif method == 'getFirstPull':
            parameter.Method = 'GET'
            parameter.Url = '%s/files' % self.BaseUrl
            query = ['"orderBy": "folder,createdTime"']
            query += ['"fields": "%s"' % g_childfields]
            query += ['"pageSize": "%s"' % g_pages]
            parameter.Query = '{%s}' % ','.join(query)
            token = uno.createUnoStruct('com.sun.star.auth.RestRequestToken')
            token.Type = TOKEN_QUERY
            token.Field = 'nextPageToken'
            token.Value = 'pageToken'
            enumerator = uno.createUnoStruct('com.sun.star.auth.RestRequestEnumerator')
            enumerator.Field = 'files'
            enumerator.Token = token
            parameter.Enumerator = enumerator
        elif method == 'getToken':
            parameter.Method = 'GET'
            parameter.Url = '%s/changes/startPageToken' % self.BaseUrl
        elif method == 'getPull':
            parameter.Method = 'GET'
            parameter.Url = '%s/changes' % self.BaseUrl
            parameter.Query = '{"pageToken": %s}' % data.getValue('Token')
            token = uno.createUnoStruct('com.sun.star.auth.RestRequestToken')
            token.Type = TOKEN_QUERY | TOKEN_SYNC
            token.Field = 'nextPageToken'
            token.Value = 'pageToken'
            token.SyncField = 'newStartPageToken'
            enumerator = uno.createUnoStruct('com.sun.star.auth.RestRequestEnumerator')
            enumerator.Field = 'changes'
            enumerator.Token = token
            parameter.Enumerator = enumerator
        elif method == 'getFolderContent':
            parameter.Method = 'GET'
            parameter.Url = '%s/files' % self.BaseUrl
            query = ['"fields": "%s"' % g_childfields]
            query += ['"pageSize": "%s"' % g_pages]
            parents = "'%s' in parents" % data.getValue('Id')
            query += ['"q": "%s"' % parents]
            parameter.Query = '{%s}' % ','.join(query)
            token = uno.createUnoStruct('com.sun.star.auth.RestRequestToken')
            token.Type = TOKEN_QUERY
            token.Field = 'nextPageToken'
            token.Value = 'pageToken'
            enumerator = uno.createUnoStruct('com.sun.star.auth.RestRequestEnumerator')
            enumerator.Field = 'files'
            enumerator.Token = token
            parameter.Enumerator = enumerator
        elif method == 'getDocumentContent':
            parameter.Method = 'GET'
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.getValue('Id'))
            mediatype = data.getValue('MediaType')
            if mediatype in g_doc_map:
                parameter.Url += '/export'
                parameter.Query = '{"mimeType": "%s"}' % mediatype
            else:
                parameter.Query = '{"alt": "media"}'
        elif method == 'updateTitle':
            parameter.Method = 'PATCH'
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.getValue('Id'))
            parameter.Json = '{"name": "%s"}' % data.getValue('Title')
        elif method == 'updateTrashed':
            parameter.Method = 'PATCH'
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.getValue('Id'))
            parameter.Json = '{"trashed": true}'
        elif method == 'updateParents':
            parameter.Method = 'PATCH'
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.getValue('Id'))
            toadd = data.getValue('ParentToAdd')
            toremove = data.getValue('ParentToRemove')
            if len(toadd) > 0:
                parameter.Json = '{"addParents": %s}' % ','.join(toadd)
            if len(toremove) > 0:
                parameter.Json = '{"removeParents": %s}' % ','.join(toremove)
        elif method == 'createNewFolder':
            parameter.Method = 'POST'
            parameter.Url = '%s/files' % self.BaseUrl
            parameter.Json = '{"id": "%s", "parents": ["%s"], "name": "%s", "mimeType": "%s"}' % \
                                (data.getValue('Id'), data.getValue('ParentId'),
                                 data.getValue('Title'), data.getValue('MediaType'))
        elif method == 'getUploadLocation':
            parameter.Method = 'PATCH'
            parameter.Url = '%s/%s' % (self.UploadUrl, data.getValue('Id'))
            parameter.Query = '{"uploadType": "resumable"}'
            parameter.Header = '{"X-Upload-Content-Type": "%s"}' % data.getValue('MediaType')
        elif method == 'getNewUploadLocation':
            parameter.Method = 'POST'
            parameter.Url = self.UploadUrl
            parameter.Query = '{"uploadType": "resumable"}'
            parameter.Json = '{"id": "%s", "parents": ["%s"], "name": "%s", "mimeType": "%s"}' % \
                                (data.getValue('Id'), data.getValue('ParentId'),
                                 data.getValue('Title'), data.getValue('MediaType'))
            parameter.Header = '{"X-Upload-Content-Type": "%s"}' % data.getValue('MediaType')
        elif method == 'getUploadStream':
            parameter.Method = 'PUT'
            parameter.Url = data.getValue('Location')
        return parameter

    def initUser(self, request, database, user):
        data = self.getToken(request, user)
        if data.IsPresent:
            token = self.getUserToken(data.Value)
            if database.updateToken(user.getValue('UserId'), token):
                user.setValue('Token', token)

    def transform(self, name, value):
        if name == 'ParentId':
            value = [value]
        return value

    def getUserId(self, user):
        return user.getValue('user').getValue('permissionId')
    def getUserName(self, user):
        return user.getValue('user').getValue('emailAddress')
    def getUserDisplayName(self, user):
        return user.getValue('user').getValue('displayName')
    def getUserToken(self, data):
        return data.getValue('startPageToken')

    def getItemParent(self, item, rootid):
        return item.getDefaultValue('parents', (rootid, ))

    def getItemId(self, item):
        return item.getDefaultValue('id', None)
    def getItemTitle(self, item):
        return item.getDefaultValue('name', None)
    def getItemCreated(self, item, timestamp=None):
        created = item.getDefaultValue('createdTime', None)
        if created:
            return self.parseDateTime(created)
        return toUnoDateTime(timestamp)
    def getItemModified(self, item, timestamp=None):
        modified = item.getDefaultValue('modifiedTime', None)
        if modified:
            return self.parseDateTime(modified)
        return toUnoDateTime(timestamp)
    def getItemMediaType(self, item):
        return item.getValue('mimeType')
    def getItemSize(self, item):
        return int(item.getDefaultValue('size', 0))
    def getItemTrashed(self, item):
        return item.getDefaultValue('trashed', False)
    def getItemCanAddChild(self, item):
        return item.getValue('capabilities').getValue('canAddChildren')
    def getItemCanRename(self, item):
        return item.getValue('capabilities').getValue('canRename')
    def getItemIsReadOnly(self, item):
        return not item.getValue('capabilities').getValue('canEdit')
    def getItemIsVersionable(self, item):
        return item.getValue('capabilities').getValue('canReadRevisions')

