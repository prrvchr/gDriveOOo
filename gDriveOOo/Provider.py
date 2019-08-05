#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE
from com.sun.star.auth.RestRequestTokenType import TOKEN_NONE
from com.sun.star.auth.RestRequestTokenType import TOKEN_URL
from com.sun.star.auth.RestRequestTokenType import TOKEN_REDIRECT
from com.sun.star.auth.RestRequestTokenType import TOKEN_QUERY
from com.sun.star.auth.RestRequestTokenType import TOKEN_JSON

# clouducp is only available after CloudUcpOOo as been loaded...
try:
    from clouducp import ProviderBase
except ImportError:
    class ProviderBase():
        pass

from gdrive import g_oauth2
from gdrive import g_plugin
from gdrive import g_host
from gdrive import g_url
from gdrive import g_upload
from gdrive import g_userfields
from gdrive import g_itemfields
from gdrive import g_childfields
from gdrive import g_pages
from gdrive import g_folder
from gdrive import g_office
from gdrive import g_link
from gdrive import g_doc_map
from gdrive import g_chunk
from gdrive import g_buffer
from gdrive import g_IdentifierRange

import json

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = '%s.Provider' % g_plugin


class Provider(ProviderBase):
    def __init__(self, ctx):
        self.ctx = ctx
        self.Scheme = ''
        self.Plugin = ''
        self.Link = ''
        self.Folder = ''
        self.SourceURL = ''
        self.SessionMode = OFFLINE
        self._Error = ''
        self.Request = self._getRequest()

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
    def GenerateIds(self):
        return True
    @property
    def IdentifierRange(self):
        return g_IdentifierRange

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
        elif method == 'getRoot' :
            parameter.Method = 'GET'
            parameter.Url = '%s/files/root' % self.BaseUrl
            parameter.Query = '{"fields": "%s"}' % g_itemfields
        elif method == 'getItem':
            parameter.Method = 'GET'
            parameter.Url = '%s/files/%s' % (self.BaseUrl, data.getValue('Id'))
            parameter.Query = '{"fields": "%s"}' % g_itemfields
        elif method == 'getFolderContent':
            parameter.Method = 'GET'
            parameter.Url = '%s/files' % self.BaseUrl
            query = "'%s' in parents" % data.getValue('Id')
            parameter.Query = '{"fields": "%s", "pageSize": "%s", "q": "%s"}' % \
                (g_childfields, g_pages, query)
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
        elif method == 'createNewFolder':
            parameter.Method = 'POST'
            parameter.Url = '%s/files' % self.BaseUrl
            parameter.Json = '{"id": "%s", "parents": "%s", "name": "%s", "mimeType": "%s"}' % \
                                (data.getValue('Id'), data.getValue('ParentId'),
                                 data.getValue('Title'), data.getValue('MediaType'))
        elif method == 'getUploadLocation':
            parameter.Method = 'PATCH'
            parameter.Url = '%s/%s' % (self.UploadUrl, data.getValue('Id'))
            parameter.Query = '{"uploadType": "resumable"}'
            parameter.Header = '{"X-Upload-Content-Type": "%s"}' % data.getValue('MediaType')
        elif method == 'getNewUploadLocation':
            mimetype = None if data.getValue('Size') else data.getValue('MediaType')
            parameter.Method = 'POST'
            parameter.Url = self.UploadUrl
            parameter.Query = '{"uploadType": "resumable"}'
            parameter.Json = '{"id": "%s", "parents": "%s", "name": "%s", "mimeType": "%s"}' % \
                                (data.getValue('Id'), data.getValue('ParentId'),
                                 data.getValue('Title'), data.getValue('MediaType'))
            parameter.Header = '{"X-Upload-Content-Type": "%s"}' % data.getValue('MediaType')
        elif method == 'getUploadStream':
            parameter.Method = 'PUT'
            parameter.Url = data.getValue('Location')
        return parameter

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
        return timestamp
    def getItemModified(self, item, timestamp=None):
        modified = item.getDefaultValue('modifiedTime', None)
        if modified:
            return self.parseDateTime(modified)
        return timestamp
    def getItemMediaType(self, item):
        return item.getValue('mimeType')
    def getItemSize(self, item):
        return item.getDefaultValue('size', 0)
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

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(Provider,
                                         g_ImplementationName,
                                        (g_ImplementationName, ))
