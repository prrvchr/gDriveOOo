#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContentProvider, IllegalIdentifierException
from com.sun.star.beans import XPropertiesChangeListener

import traceback

from gdrive import Component
from gdrive import getResourceLocation, createService, getItem, getUri, getCommand, getProperty
from gdrive import getUserInsert, executeUserInsert
from gdrive import getItemInsert, getItemUpdate, executeItemInsert, executeItemUpdate
from gdrive import CommandEnvironment, getLogger

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider'

g_Scheme = 'vnd.google-apps'


class ContentProvider(unohelper.Base, Component, XServiceInfo, XContentProvider, XPropertiesChangeListener):
    def __init__(self, ctx):
        try:
            print("ContentProvider.__init__()")
            self.ctx = ctx
            self._UserName = None
            
            url = getResourceLocation(self.ctx, '%s.odb' % g_Scheme)
            db = createService('com.sun.star.sdb.DatabaseContext').getByName(url)
            connection = db.getConnection('', '')
            
            self.userInsert = getUserInsert(connection)
            self.itemInsert = getItemInsert(connection)
            self.itemUpdate = getItemUpdate(connection)
            query = uno.getConstantByName('com.sun.star.sdb.CommandType.QUERY')
            self.userSelect = connection.prepareCommand('getRoot', query)
            self.itemSelect = connection.prepareCommand('getItem', query)
            scroll = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_SENSITIVE')
            self.itemSelect.ResultSetType = scroll
            concurrency = uno.getConstantByName('com.sun.star.sdbc.ResultSetConcurrency.UPDATABLE')
            self.itemSelect.ResultSetConcurrency = concurrency
            self.Root = {}
            
            self.cachedContent = {}
            self.Logger = getLogger(self.ctx)
            print("ContentProvider.__init__()")
        except Exception as e:
            print("ContentProvider.__init__().Error: %s" % e)

    @property
    def UserName(self):
        return self._UserName
    @UserName.setter
    def UserName(self, username):
        if self._UserName != username:
            if not self._getRoot(username):
                raise IllegalIdentifierException('Identifier has no Authority: %s' % username, self)
            self.itemSelect.setString(1, username)

    # XPropertiesChangeListener
    def propertiesChange(self, events):
        for event in events:
            if self._updateItem(event):
                level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", "Property saved: %s" % event.PropertyName)
            else:
                level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", "Can't save Property: %s" % event.PropertyName)                
    def disposing(self, source):
        print("ContentProvider.disposing() %s" % (source, ))

    # XParameterizedContentProvider
    def registerInstance(self, template, argument, replace):
        print("ContentProvider.registerInstance() ****************************************")
    def deregisterInstance(self, template, argument):
        print("ContentProvider.deregisterInstance() ****************************************")

    # XContentProvider
    def queryContent(self, identifier):
        try:
            uri = getUri(self.ctx, identifier.getContentIdentifier())
            if not uri.hasAuthority():
                raise IllegalIdentifierException('Identifier has no Authority: %s' % identifier.getContentIdentifier(), self)
            self.UserName = uri.getAuthority()
            id = self._getItemId(uri)
            if id not in self.cachedContent:
                self.itemSelect.setString(2, id)
                media = 'application/octet-stream'
                arguments = self.Root
                result = self.itemSelect.executeQuery()
                if result.next():
                    media, arguments = self._getMediaTypeFromResult(result)
                else:
                    json = getItem(self.ctx, g_Scheme, self.UserName, id)
                    if executeItemInsert(self.itemInsert, json):
                        result = self.itemSelect.executeQuery()
                        if result.next():
                            media, arguments = self._getMediaTypeFromResult(result)
                name = 'com.gmail.prrvchr.extensions.gDriveOOo.'
                if media == 'application/vnd.google-apps.folder':
                    name += 'DriveFolderContent' if id != self.Root['Id'] else 'DriveRootContent'
                elif media.startswith('application/vnd.oasis.opendocument'):
                    name += 'DriveOfficeContent'
                else:
                    raise IllegalIdentifierException('ContentType is unknown: %s' % media, self)
                print("ContentProvider.queryContent() 2: %s" % name)
                service = createService(name, self.ctx, **arguments)
                service.addPropertiesChangeListener(('IsInCache', 'Title'), self)
                self.cachedContent[id] = service
                print("ContentProvider.queryContent() 3:")
            return self.cachedContent[id]
        except Exception as e:
            print("ContentProvider.queryContent().Error: %s - %s" % (e, traceback.print_exc()))

    def compareContentIds(self, identifier1, identifier2):
        uri1 = getUri(identifier1.getContentIdentifier())
        uri2 = getUri(identifier2.getContentIdentifier())
        print("ContentProvider.compareContentIds(): %s - %s" % (id1, id2))
        if uri1 == uri2:
            print("ContentProvider.compareContentIds() ************")
            return 0
        if uri1.getScheme() != uri2.getScheme() or uri1.getAuthority() != uri2.getAuthority():
            print("ContentProvider.compareContentIds() ------------")
            return -1
        print("ContentProvider.compareContentIds() ------------")
        return 1

    def _updateItem(self, event):
        query = 'UPDATE "Item" SET "%s" = ?, "TimeStamp" = NOW() WHERE "Id" = ?' % event.PropertyName
        update = getItemUpdate(self.itemUpdate.getConnection(), query)
        id = self._getContentProperties(event.Source, ('Id', )).getString(1)
        update.setString(2, id)
        if event.PropertyName == 'IsInCache':
            update.setBoolean(1, event.NewValue)
        elif event.PropertyName == 'Title':
            update.setString(1, event.NewValue)
        return update.executeUpdate()

    def _getContentProperties(self, content, names):
        properties = []
        for name in names:
            properties.append(getProperty(name))
        command = getCommand('getPropertyValues', tuple(properties))
        row = content.execute(command, 0, CommandEnvironment())
        return row

    def _getItemId(self, uri):
        id = self.Root['Id']
        if uri.getPathSegmentCount() > 0:
            path = uri.getPathSegment(uri.getPathSegmentCount() -1)
            if path not in ('', '.', 'root'):
                id = path
        return id

    def _getRoot(self, username):
        self.userSelect.setString(1, username)
        result = self.userSelect.executeQuery()
        if result.next():
            self.Root = self._getArgumentsFromResult(result)
            return True
        else:
            json = getItem(self.ctx, g_Scheme, username, 'root')
            if 'id' in json:
                executeUserInsert(self.userInsert, username, json['id'])
                executeItemUpdate(self.itemInsert, self.itemUpdate, json)
                result = self.userSelect.executeQuery()
                if result.next():
                    self.Root = self._getArgumentsFromResult(result)
                    return True
        return False

    def _getMediaTypeFromResult(self, result):
        arguments = self._getArgumentsFromResult(result)
        return arguments['MediaType'], arguments

    def _getArgumentsFromResult(self, result):
        arguments = {}
        arguments['Scheme'] = result.getColumns().getByName('Scheme').getString()
        arguments['UserName'] = result.getColumns().getByName('UserName').getString()
        arguments['Id'] = result.getColumns().getByName('Id').getString()
        if result.getColumns().hasByName('ParentId'):
            arguments['ParentId'] = result.getColumns().getByName('ParentId').getString()
        else:
            arguments['ParentId'] = None
        arguments['Title'] = result.getColumns().getByName('Title').getString()
        arguments['MediaType'] = result.getColumns().getByName('MediaType').getString()
        arguments['DateCreated'] = result.getColumns().getByName('DateCreated').getTimestamp()
        arguments['DateModified'] = result.getColumns().getByName('DateModified').getTimestamp()
        arguments['Size'] = result.getColumns().getByName('Size').getLong()
        arguments['IsReadOnly'] = result.getColumns().getByName('IsReadOnly').getBoolean()
        arguments['CanRename'] = result.getColumns().getByName('CanRename').getBoolean()
        arguments['CanAddChild'] = result.getColumns().getByName('CanAddChild').getBoolean()
        arguments['IsInCache'] = result.getColumns().getByName('IsInCache').getBoolean()
        arguments['IsVersionable'] = result.getColumns().getByName('IsVersionable').getBoolean()
        arguments['BaseURI'] = result.getColumns().getByName('BaseURI').getString()
        arguments['TargetURL'] = result.getColumns().getByName('TargetURL').getString()
        arguments['TitleOnServer'] = result.getColumns().getByName('TitleOnServer').getString()
        arguments['CasePreservingURL'] = result.getColumns().getByName('CasePreservingURL').getString()
        return arguments

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(ContentProvider,                                                    # UNO object class
                                         g_ImplementationName,                                               # Implementation name
                                        (g_ImplementationName, 'com.sun.star.ucb.ContentProvider'))          # List of implemented services
