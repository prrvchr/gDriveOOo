#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import IllegalIdentifierException

from gdrive import ChildGenerator
from gdrive import InputStream
from gdrive import OutputStream

from gdrive import getItem
from gdrive import isIdentifier
from gdrive import getNewIdentifier
from gdrive import selectChildId
from gdrive import updateItem
from gdrive import setJsonData

from gdrive import g_doc_map
from gdrive import g_folder
from gdrive import g_link
from gdrive import g_plugin

# clouducp is only available after CloudUcpOOo as been loaded...
try:
    from clouducp import ContentIdentifierBase
except ImportError:
    class ContentIdentifierBase():
        pass
# requests is only available after OAuth2OOo as been loaded...
try:
    from oauth2.requests.compat import unquote_plus
except ImportError:
    def unquote_plus():
        pass


# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = '%s.ContentIdentifier' % g_plugin


class ContentIdentifier(ContentIdentifierBase,
                        XServiceInfo):
    def __init__(self, ctx, *namedvalues):
        ContentIdentifierBase.__init__(self, ctx, namedvalues)
    @property
    def Properties(self):
        print("gDriveOOo.ContentIdentifier.Properties")
        return ('Name', 'DateCreated', 'DateModified', 'MimeType', 'Size', 'Trashed',
                'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable', 'Loaded')

    def getPlugin(self):
        return g_plugin
    def getFolder(self):
        return g_folder
    def getLink(self):
        return g_link
    def getDocument(self):
        return g_doc_map
    def doSync(self, session):
        return doSync(self.ctx, self.User.Connection, session, self.SourceURL, self.User.Id)
    def updateChildren(self, session):
        merge, index = self.mergeJsonItemCall()
        update = all(self.mergeJsonItem(merge, item, index) for item in ChildGenerator(session, self.Id))
        merge.close()
        return update
    def getNewIdentifier(self):
        return getNewIdentifier(self.User.Connection, self.User.Id)
    def getItem(self, session):
        return getItem(session, self.Id)
    def selectItem(self):
        item = None
        select = self.User.Connection.prepareCall('CALL "selectItem"(?, ?)')
        select.setString(1, self.User.Id)
        select.setString(2, self.Id)
        result = select.executeQuery()
        if result.next():
            item = self.getItemFromResult(result, self.Properties)
        select.close()
        return item
    def insertJsonItem(self, item):
        item = None
        insert = self.User.Connection.prepareCall('CALL "insertJsonItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        insert.setString(1, self.User.Id)
        index = setJsonData(insert, item, self.getDateTimeParser(), self.unparseDateTime(), 2)
        parents = ','.join(item.get('parents', self.User.RootId))
        insert.setString(index, parents)
        result = insert.executeQuery()
        if result.next():
            item = self.getItemFromResult(result, self.Properties)
        insert.close()
        return item
    def isIdentifier(self, title):
        return isIdentifier(self.User.Connection, self.User.Id, title)
    def selectChildId(self, parent, title):
        return selectChildId(self.User.Connection, self.User.Id, parent, title)
    def unquote(self, text):
        return unquote_plus(text)
    def mergeJsonItemCall(self):
        merge = self.User.Connection.prepareCall('CALL "mergeJsonItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        merge.setString(1, self.User.Id)
        return merge, 2
    def mergeJsonItem(self, merge, item, index=1):
        index = setJsonData(merge, item, self.getDateTimeParser(), self.unparseDateTime(), index)
        parents = ','.join(item.get('parents', self.User.RootId))
        merge.setString(index, parents)
        merge.execute()
        return merge.getLong(index +1)
    def getItemToSync(self, mode):
        items = []
        transform = {'parents': lambda value: value.split(',')}
        select = self.User.Connection.prepareCall('CALL "selectSync"(?, ?)')
        select.setString(1, self.User.Id)
        select.setLong(2, mode)
        result = select.executeQuery()
        while result.next():
            items.append(self.getItemFromResult(result, None, transform))
        select.close()
        return items
    def syncItem(self, session, path, item):
        result = False
        id = item.get('id')
        mode = item.get('mode')
        data = None 
        if mode & self.CREATED:
            data = {'id': id,
                    'parents': item.get('parents'),
                    'name': item.get('name'),
                    'mimeType': item.get('mimeType')}
            if mode & self.FOLDER:
                result = updateItem(session, id, data, True)
            if mode & self.FILE:
                mimetype = item.get('mimeType')
                result = self.uploadItem(session, path, id, data, mimetype, True)
        else:
            if mode & self.REWRITED:
                mimetype = None if item.get('size') else item.get('mimeType')
                result = self.uploadItem(session, path, id, data, mimetype, False)
            if mode & self.RENAMED:
                data = {'name': item.get('name')}
                result = updateItem(session, id, data, False)
        if mode & self.TRASHED:
            data = {'trashed': True}
            result = updateItem(session, id, data, False)
        return result
    def uploadItem(session, path, id, data, mimetype, new):
        size, stream = self.getInputStream(path, id)
        if size: 
            location = getUploadLocation(session, id, data, mimetype, new, size)
            if location is not None:
                mimetype = None
                pump = self.ctx.ServiceManager.createInstance('com.sun.star.io.Pump')
                pump.setInputStream(stream)
                pump.setOutputStream(OutputStream(session, location, size))
                pump.start()
                return id
        return False

    # XInputStreamProvider
    def createInputStream(self):
        return InputStream(self.Session, self.Id, self.Size, self.MimeType)

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(ContentIdentifier,                                                  # UNO object class
                                         g_ImplementationName,                                               # Implementation name
                                        (g_ImplementationName, ))                                            # List of implemented services
