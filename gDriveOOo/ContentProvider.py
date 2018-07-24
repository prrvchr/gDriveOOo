#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContentProvider, IllegalIdentifierException

import gdrive
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider'

g_Scheme = 'vnd.google-apps'


class ContentProvider(unohelper.Base, XServiceInfo, XContentProvider):
    def __init__(self, ctx):
        try:
            print("ContentProvider.__init__()")
            self.ctx = ctx
            url = gdrive.getResourceLocation(self.ctx, '%s.odb' % g_Scheme)
            db = self.ctx.ServiceManager.createInstance("com.sun.star.sdb.DatabaseContext").getByName(url)
            self.connection = db.getConnection('', '')
            self.Item = gdrive.Item(self.ctx, g_Scheme, self.connection)
            print("ContentProvider.__init__()")
        except Exception as e:
            print("ContentProvider.__init__().Error: %s" % e)

    # XParameterizedContentProvider
    def registerInstance(self, template, argument, replace):
        print("ContentProvider.registerInstance() ****************************************")
    def deregisterInstance(self, template, argument):
        print("ContentProvider.deregisterInstance() ****************************************")

    # XContentProvider
    def queryContent(self, identifier):
        try:
            print("ContentProvider.queryContent() 1: %s" % identifier.getContentIdentifier())
            uri = gdrive.getUri(self.ctx, identifier.getContentIdentifier())
            if not uri.hasAuthority():
                raise IllegalIdentifierException('Identifier has no Authority: %s' % identifier.getContentIdentifier(), self)
            id = self._getFileId(uri)
            if not self._checkFileId(id):
                raise IllegalIdentifierException('Identifier is no valid: %s' % identifier.getContentIdentifier(), self)
            print("ContentProvider.queryContent() 2")
            self.Item.UserName = uri.getAuthority()
            print("ContentProvider.queryContent() 3")
            content, id = self.Item.get(id).execute()
            if content is None:
                raise IllegalIdentifierException('ContentType is unknown: %s' % identifier.getContentIdentifier(), self)
            print("ContentProvider.queryContent() 4")
            service = self._queryContent(content, id)
            print("ContentProvider.queryContent() 5")
            return service
        except Exception as e:
            print("ContentProvider.queryContent().Error: %s - %s" % (e, traceback.print_exc()))

    def compareContentIds(self, identifier1, identifier2):
        uri1 = gdrive.getUri(identifier1.getContentIdentifier())
        uri2 = gdrive.getUri(identifier2.getContentIdentifier())
        id1 = self._getFileId(uri1)
        id2 = self._getFileId(uri2)
        print("ContentProvider.compareContentIds(): %s - %s" % (id1, id2))
        if id1 == id2:
            print("ContentProvider.compareContentIds() ************")
            return 0
        if uri1.getScheme() != uri2.getScheme() or uri1.getAuthority() != uri2.getAuthority():
            print("ContentProvider.compareContentIds() ------------")
            return -1
        print("ContentProvider.compareContentIds() ------------")
        return 1


    def _queryContent(self, content, id):
        try:
            print("ContentProvider._queryContent() 1: %s" % content)
            arguments = {'Scheme': g_Scheme, 'UserName': self.Item.UserName, 'FileId': id, 'Connection': self.connection}
            name = 'com.gmail.prrvchr.extensions.gDriveOOo.'
            if content == 'application/vnd.google-apps.folder-root':
                name += 'DriveRootContent'
            elif content == 'application/vnd.google-apps.folder-search':
                name += 'GoogleDriveSearchContent'
            elif content == 'application/vnd.google-apps.folder':
                name += 'DriveFolderContent'
            elif content == 'application/vnd.google-apps.drive-sdk':
                name += 'GoogleDriveLinkContent'
            elif content == 'application/vnd.google-apps.document':
                name += 'GoogleDriveDocumentContent'
            elif content == 'application/vnd.oasis.opendocument':
                name += 'DriveOfficeContent'
            else:
                name += 'GoogleDriveFileContent'
            print("ContentProvider._queryContent() 2: %s" % name)
            service = gdrive.createService(name, self.ctx, **arguments)
            print("ContentProvider._queryContent() 3:")
            return service
        except Exception as e:
            print("ContentProvider._queryContent().Error: %s" % e)

    def _getFileId(self, uri):
        id = None
        if uri.getPathSegmentCount() > 0:
            path = uri.getPathSegment(uri.getPathSegmentCount() -1)
            if path == '' or path == 'root' or path == '.':
                id = 'root'
            else:
                id = path
        else:
            id = 'root'
        return id

    def _checkFileId(self, id):
        if id is None:
            return False
        elif id == 'root':
            return True
        elif '.' not in id and ' ' not in id and len(id) > 18 and len(id) < 34:
            return True
        return False

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(ContentProvider,                           # UNO object class
                                         g_ImplementationName,                      # Implementation name
                                        (g_ImplementationName,))                    # List of implemented services
