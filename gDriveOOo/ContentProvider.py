#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory, IllegalIdentifierException
from com.sun.star.beans import XPropertiesChangeListener
from com.sun.star.awt import XCallback

import traceback

from gdrive import Component, ContentIdentifier
from gdrive import getDbConnection, getRootSelect, executeUserInsert, executeUpdateInsertItem
from gdrive import getItemSelect, getItemInsert, updateItem, getContentProperties
from gdrive import insertParent, getItemUpdate, executeItemInsert

from gdrive import getResourceLocation, createService, getItem, getUri, getProperty
from gdrive import getLogger, queryContentIdentifier
from gdrive import getNewId, getId

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider'

g_Scheme = 'vnd.google-apps'


class ContentProvider(unohelper.Base, Component, XServiceInfo, XContentProvider,
                      XContentIdentifierFactory, XPropertiesChangeListener, XCallback):
    def __init__(self, ctx):
        try:
            print("ContentProvider.__init__()")
            self.ctx = ctx
            self.UserName = None
            self.Root = {}
            self.Logger = getLogger(self.ctx)
            self.listener = []
            #self.Connection = getDbConnection(self.ctx, g_Scheme, True)
            #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
            #mri.inspect(self.connection)
            print("ContentProvider.__init__()")
        except Exception as e:
            print("ContentProvider.__init__().Error: %s" % e)

    # XComponent
    def dispose(self):
        print("ContentProvider.dispose() 1")
        event = uno.createUnoStruct('com.sun.star.lang.EventObject', self)
        for listener in self.listeners:
            listener.disposing(event)
        print("ContentProvider.dispose() 2 ********************************************************")
    def addEventListener(self, listener):
        print("ContentProvider.addEventListener() *************************************************")
        if listener not in self.listeners:
            self.listeners.append(listener)
    def removeEventListener(self, listener):
        print("ContentProvider.removeEventListener() **********************************************")
        if listener in self.listeners:
            self.listeners.remove(listener)

    # XCallback
    def notify(self, event):
        if event.Action == uno.getConstantByName('com.sun.star.ucb.ContentAction.INSERTED'):
            properties = ('Id', 'Title', 'DateCreated', 'DateModified', 'MediaType', 'ParentId')
            row = getContentProperties(event.Content, properties)
            id = row.getString(1)
            connection = getDbConnection(self.ctx, g_Scheme)
            insert = getItemInsert(connection)
            insert.setString(1, id)
            insert.setString(2, row.getString(2))
            insert.setTimestamp(3, row.getTimestamp(3))
            insert.setTimestamp(4, row.getTimestamp(4))
            insert.setString(5, row.getString(5))
            insert.setBoolean(6, False)
            insert.setBoolean(7, True)
            insert.setBoolean(8, True)
            insert.setDouble(9, 0)
            if insert.executeUpdate():
                if insertParent(connection, {'Id': id, 'ParentId': row.getString(6)}):
                    print("ContentProvider.notify(): %s" % id)
                    event.Content.addPropertiesChangeListener(('IsInCache', 'Title', 'Size'), self)
                    parent = self.queryContent(event.Id)
                    parent.notify(event)
            connection.close()

    # XPropertiesChangeListener
    def propertiesChange(self, events):
        connection = getDbConnection(self.ctx, g_Scheme)
        for event in events:
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            id = getContentProperties(event.Source, ('Id', )).getString(1)
            self.Logger.logp(level, "ContentProvider", "propertiesChange()", "Id: %s Property saved: %s ..." % (id, event.PropertyName))
            if updateItem(connection, id, event.PropertyName, event.NewValue):
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", "Id: %s Property saved: %s ... Done" % (id, event.PropertyName))
            else:
                level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", "Id: %s Can't save Property: %s" % (id, event.PropertyName))
        connection.close()
    def disposing(self, source):
        print("ContentProvider.disposing() %s" % (source, ))

    # XContentIdentifierFactory
    def createContentIdentifier(self, identifier):
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", "Identifier: %s ..." % identifier)
        uri = getUri(self.ctx, identifier)
        if uri.hasAuthority() and self.UserName != uri.getAuthority():
            self._setUserName(uri.getAuthority())
        elif self.UserName is None:
            raise IllegalIdentifierException('Identifier has no Authority: %s' % identifier, self)
        id = getId(uri, self.Root['Id'])
        if id == 'new':
            connection = getDbConnection(self.ctx, g_Scheme)
            id = getNewId(self.ctx, g_Scheme, self.UserName, connection)
            connection.close()
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", "New Identifier: %s ..." % id)
        identifier = '%s://%s/%s' % (g_Scheme, self.UserName, id)
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", "Identifier: %s ... Done" % identifier)
        return ContentIdentifier(g_Scheme, identifier)

    # XParameterizedContentProvider
    def registerInstance(self, template, argument, replace):
        print("ContentProvider.registerInstance() ****************************************")
    def deregisterInstance(self, template, argument):
        print("ContentProvider.deregisterInstance() ****************************************")

    # XContentProvider
    def queryContent(self, identifier):
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
        self.Logger.logp(level, "ContentProvider", "queryContent()", "Identifier: %s..." % identifier.getContentIdentifier())
        media = 'application/vnd.google-apps.folder'
        arguments = self.Root
        connection = getDbConnection(self.ctx, g_Scheme)
        uri = getUri(self.ctx, identifier.getContentIdentifier())
        if uri.hasAuthority() and self.UserName != uri.getAuthority():
            self._setUserName(uri.getAuthority())
        elif self.UserName is None:
            raise IllegalIdentifierException('Identifier has no Authority: %s' % identifier.getContentIdentifier(), self)
        id = getId(uri)
        select = getItemSelect(connection, id)
        result = select.executeQuery()
        if result.next():
            media, arguments = self._getMediaTypeFromResult(result)
        else:
            status, item = getItem(self.ctx, g_Scheme, self.UserName, id)
            if status and executeItemInsert(connection, item):
                result = select.executeQuery()
                if result.next():
                    media, arguments = self._getMediaTypeFromResult(result)
            else:
                raise IllegalIdentifierException('Invalid Identifier: %s' % identifier.getContentIdentifier(), self)
        connection.close()
        name = 'com.gmail.prrvchr.extensions.gDriveOOo.'
        if media == 'application/vnd.google-apps.folder':
            name += 'DriveFolderContent' if id != self.Root['Id'] else 'DriveRootContent'
        elif media.startswith('application/vnd.oasis.opendocument'):
            name += 'DriveOfficeContent'
        else:
            raise IllegalIdentifierException('ContentType is unknown: %s' % media, self)
        service = createService(name, self.ctx, **arguments)
        service.addPropertiesChangeListener(('IsInCache', 'Title', 'Size'), self)
        self.Logger.logp(level, "ContentProvider", "queryContent()", "Identifier: %s... Done" % identifier.getContentIdentifier())
        return service

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

    def _setUserName(self, username):
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
        self.Logger.logp(level, "ContentProvider", "UserName.setter()", "UserName: %s..." % username)
        if self._getRoot(username):
            self.UserName = username
            self.Logger.logp(level, "ContentProvider", "UserName.setter()", "UserName: %s... Done" % username)
        else:
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
            self.Logger.logp(level, "ContentProvider", "UserName.setter()", "UserName: %s... ERROR" % username)
            raise IllegalIdentifierException('Identifier has no Authority: %s' % username, self)

    def _getRoot(self, username):
        retrived = False
        connection = getDbConnection(self.ctx, g_Scheme)
        select = getRootSelect(connection, username)
        result = select.executeQuery()
        if result.next():
            self.Root = self._getArgumentsFromResult(result, username)
            retrived = True
        else:
            status, item = getItem(self.ctx, g_Scheme, username, 'root')
            if status and executeUserInsert(connection, username, item['id']) and executeUpdateInsertItem(connection, item):
                result = select.executeQuery()
                if result.next():
                    self.Root = self._getArgumentsFromResult(result, username)
                    retrived = True
        connection.close()
        return retrived

    def _getMediaTypeFromResult(self, result):
        arguments = self._getArgumentsFromResult(result, self.UserName)
        return arguments['MediaType'], arguments

    def _getArgumentsFromResult(self, result, username):
        arguments = {'Scheme': g_Scheme, 'UserName': username, 'Logger': self.Logger}
        for index in range(1, result.MetaData.ColumnCount +1):
            dbtype = result.MetaData.getColumnTypeName(index)
            if dbtype == 'VARCHAR':
                value = result.getString(index)
            elif dbtype == 'TIMESTAMP':
                value = result.getTimestamp(index)
            elif dbtype == 'BOOLEAN':
                value = result.getBoolean(index)
            elif dbtype == 'BIGINT':
                value = result.getLong(index)
            arguments[result.MetaData.getColumnName(index)] = value
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
