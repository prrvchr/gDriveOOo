#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo, XComponent
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory, XParameterizedContentProvider
from com.sun.star.ucb import URLAuthenticationRequest, IllegalIdentifierException
from com.sun.star.beans import XPropertiesChangeListener
from com.sun.star.frame import XTerminateListener, TerminationVetoException

import traceback

from gdrive import ContentIdentifier
from gdrive import getDbConnection, getUserSelect, getUserInsert, executeUserInsert, executeUpdateInsertItem
from gdrive import getItemSelect, getItemInsert, getItemUpdate, getContentProperties, getUcb
from gdrive import executeItemInsert, getChildDelete, getChildInsert, setContentProperties

from gdrive import createService, getItem, getUri, getUriPath, getProperty
from gdrive import getLogger, insertContent, updateContent, getParentUri
from gdrive import getNewId, getId, getIdSelect, getIdInsert, getIdUpdate

from requests import codes

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider'


class ContentProvider(unohelper.Base, XComponent, XServiceInfo, XContentProvider,
                      XContentIdentifierFactory, XPropertiesChangeListener,
                      XParameterizedContentProvider, XTerminateListener):
    def __init__(self, ctx):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "ContentProvider loading ..."
        self.ctx = ctx
        self.Scheme = None          #'vnd.google-apps'
        self.UserName = None
        self.Root = {}
        self.currentFolder = None
        self.listeners = []
        self.cachedContent = {}
        self.Logger = getLogger(self.ctx)
        msg += " Done"
        self.Logger.logp(level, "ContentProvider", "__init__()", msg)

    @property
    def RootId(self):
        return self.Root['Id'] if 'Id' in self.Root else ''
    @property
    def RootUri(self):
        return self.Root['Uri'] if 'Uri' in self.Root else getUri(self.ctx, '%s://%s/' % (self.Scheme, self.UserName))

    # XParameterizedContentProvider
    def registerInstance(self, template, arguments, replace):
        ucb = getUcb(self.ctx)
        self.Scheme = template
        self._initDataBase()
        return ucb.registerContentProvider(self, self.Scheme, replace)
    def deregisterInstance(self, template, argument):
        ucb = getUcb(self.ctx)
        ucb.deregisterContentProvider(self, self.Scheme)

    # XTerminateListener
    def queryTermination(self, event):
        # ToDo: Upload modified metadata/files after asking user
        pass
    def notifyTermination(self, event):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Shutdown database ..."
        connection = self.statement.getConnection()
        if connection.isClosed():
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg += " connection alredy closed !!!"
        else:
            self._shutdownDataBase()
            msg += "closing connection ..."
        msg += " Done"
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", msg)

    # XComponent
    def dispose(self):
        print("ContentProvider.dispose() ****************************************************")
        event = uno.createUnoStruct('com.sun.star.lang.EventObject', self)
        for listener in self.listeners:
            listener.disposing(event)
    def addEventListener(self, listener):
        if listener not in self.listeners:
            self.listeners.append(listener)
    def removeEventListener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)

    # XPropertiesChangeListener
    def propertiesChange(self, events):
        for event in events:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            if event.PropertyName == 'Id':
                msg = "Item inserted new Id: %s ..." % event.NewValue
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
                if insertContent(self.ctx, event, self.itemInsert, self.childInsert, self.idUpdate, self.RootId):
                    msg = "Item inserted new Id: %s ... Done" % event.NewValue
                else:
                    level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                    msg = "ERROR: Can't insert new Id: %s" % event.NewValue
            else:
                msg = "Item updated Property: %s ..." % event.PropertyName
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
                if updateContent(event, self.statement):
                    msg = "Item updated Property: %s ... Done" % event.PropertyName
                else:
                    level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                    msg = "ERROR: Can't update Property: %s" % event.PropertyName
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
    def disposing(self, source):
        pass

    # XContentIdentifierFactory
    def createContentIdentifier(self, identifier):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifier: %s ..." % identifier
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        uri = getUri(self.ctx, identifier)
        if not self._checkAuthority(uri):
            raise IllegalIdentifierException('Identifier has no Authority: %s' % identifier, self)
        id = getId(uri, self.RootId)
        if id == 'new':
            msg = "New Identifier: %s ..." % uri.getUriReference()
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
            id = getNewId(self.ctx, self.Scheme, self.UserName, self.idSelect, self.idInsert)
            path = getUriPath(uri, id, True)
            identifier = '%s://%s/%s' % (self.Scheme, uri.getAuthority(), '/'.join(path))
            uri = getUri(self.ctx, identifier)
            msg = "New Identifier: %s ... Done" % uri.getUriReference()
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)  
        elif id in ('.', ''):
            uri = self.RootUri if self.currentFolder is None else self.currentFolder
        msg = "Identifier: %s ... Done" % uri.getUriReference()
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        return ContentIdentifier(uri)


    # XContentProvider
    def queryContent(self, identifier):
        identifier = identifier.getContentIdentifier()
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifier: %s..." % identifier
        uri = getUri(self.ctx, identifier)
        if not self._checkAuthority(uri):
            raise IllegalIdentifierException('Identifier has no Authority: %s' % identifier, self)
        id = getId(uri, self.RootId)
        if id == '':
            raise IllegalIdentifierException('Identifier has illegal Path: %s' % identifier, self)
        retrived, content = self._getContent(id, uri)
        if not retrived:
            raise IllegalIdentifierException('Identifier has not been retrived: %s' % id, self)
        if not getContentProperties(content, ('IsFolder', )).getBoolean(1):
            self.currentFolder = getParentUri(self.ctx, uri)
        msg += " Done"
        self.Logger.logp(level, "ContentProvider", "queryContent()", msg)
        return content

    def compareContentIds(self, identifier1, identifier2):
        compare = 1
        identifier1 = identifier1.getContentIdentifier()
        identifier2 = identifier2.getContentIdentifier()
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifiers: %s - %s ..." % (identifier1, identifier2)
        uri1 = getUri(self.ctx, identifier1)
        uri2 = getUri(self.ctx, identifier2)
        id1 = getId(uri1, self.RootId)
        id2 = getId(uri2, self.RootId)
        if id1 == id2:
            msg += " seem to be the same..."
            compare = 0
        elif uri1.getPathSegmentCount() != uri2.getPathSegmentCount():
            msg += " are not the same..."
            compare = uri1.getPathSegmentCount() - uri2.getPathSegmentCount()
        else:
            msg += " are not the same..."
        msg += " Done"
        self.Logger.logp(level, "ContentProvider", "compareContentIds()", msg)
        return compare

    def _checkAuthority(self, uri):
        if uri.hasAuthority() and uri.getAuthority() != '' and uri.getAuthority() != self.UserName:
            return self._getUserName(uri.getAuthority())
        elif self.UserName is None:
            # Todo InterActionHandler here to retreive UserName!!!
            e = URLAuthenticationRequest()
            e.URL = self.Scheme
            e.HasRealm = False
            e.HasUserName = False
            e.HasPassword = False
            e.HasAccount = True
            e.Classification = uno.getConstantByName('com.sun.star.task.ClassifiedInteractionRequest.QUERY')
            e.Message = "Authentication is needed!!!"
            e.Context = self
            raise e
        return True

    def _getUserName(self, username):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "UserName have been changed ..."
        self.Logger.logp(level, "ContentProvider", "_getUserName()", msg)
        self.userSelect.setString(1, username)
        result = self.userSelect.executeQuery()
        if result.next():
            retrived, self.UserName, self.Root = self._getUserFromDataBase(result, username)
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "UserName retreive from database ... Done"
            self.Logger.logp(level, "ContentProvider", "_getUserFromDataBase()", msg)
        else:
            retrived, self.UserName, self.Root = self._getUserFromProvider(username)
        result.close()
        return retrived

    def _getUserFromDataBase(self, result, username):
        root = self._getItemFromResult(result, username)
        return True, username, root

    def _getUserFromProvider(self, username):
        retrived = False
        root = {}
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        msg = None
        status, json = getItem(self.ctx, self.Scheme, username, 'root')
        if status is None:
            msg = "ERROR: Can't retreive from provider UserName: %s" % username
        elif status == codes.ok:
            if executeUserInsert(self.userInsert, username, json['id']) and \
               executeUpdateInsertItem(self.itemUpdate, self.itemInsert, json):
                result = self.userSelect.executeQuery()
                if result.next():
                    retrived, username, root = self._getUserFromDataBase(result, username)
                    level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
                    msg = "UserName retreive from provider ... Done"
                result.close()
            else:
                msg = "ERROR: Can't insert new User in databse UserName: %s" % username
        elif status == codes.bad_request:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        if msg is not None:
            self.Logger.logp(level, "ContentProvider", "_getUserFromProvider()", msg)
        return retrived, username, root

    def _getContent(self, id, uri):
        retrived = id in self.cachedContent
        if retrived:
            content = self.cachedContent[id]
            # a Content can have multiple parent...
            setContentProperties(content, {'Uri': uri})
        else:
            retrived, content = self._createContent(id, uri)
        return retrived, content

    def _createContent(self, id, uri):
        content = None
        retrived, item = self._getItem(id)
        if retrived:
            item.update({'Uri': uri})
            name = None
            media = item['MediaType']
            if media == 'application/vnd.google-apps.folder':
                statements = {'itemUpdate': self.itemUpdate, 'itemInsert': self.itemInsert,
                             'childDelete': self.childDelete, 'childInsert': self.childInsert}
                item.update(statements)
                name = 'DriveFolderContent' if id != self.RootId else 'DriveRootContent'
            elif media.startswith('application/vnd.oasis.opendocument'):
                name = 'DriveOfficeContent'
            if name:
                service = 'com.gmail.prrvchr.extensions.gDriveOOo.%s' % name
                content = createService(service, self.ctx, **item)
                content.addPropertiesChangeListener(('IsWrite', 'IsRead', 'Title', 'Size'), self)
                self.cachedContent[id] = content
        return retrived, content

    def _getItem(self, id):
        retrived, item = False, {}
        if id != 'root':
            self.itemSelect.setString(1, id)
            result = self.itemSelect.executeQuery()
            if result.next():
                retrived, item = self._getItemFromDataBase(result)
            else:
                retrived, item = self._getItemFromProvider(id)
            result.close()
        return retrived, item

    def _getItemFromDataBase(self, result):
        item = self._getItemFromResult(result, self.UserName)
        return True, item

    def _getItemFromProvider(self, id):
        retrived = False
        item = {}
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        msg = None
        status, json = getItem(self.ctx, self.Scheme, self.UserName, id)
        if status is None:
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        elif status == codes.ok:
            if executeItemInsert(self.itemInsert, json):
                result = self.itemSelect.executeQuery()
                if result.next():
                    retrived, item = self._getItemFromDataBase(result)
                result.close()
            else:
                msg = "ERROR: Can't insert new Item in databse Id: %s" % id
        elif status == codes.bad_request:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        if msg is not None:
            self.Logger.logp(level, "ContentProvider", "_getItemFromProvider()", msg)            
        return retrived, item

    def _getItemFromResult(self, result, username):
        item = {'UserName': username}
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
            if result.wasNull():
                value = None
            item[result.MetaData.getColumnName(index)] = value
        return item

    def _initDataBase(self):
        desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
        desktop.addTerminateListener(self)
        connection = getDbConnection(self.ctx, self.Scheme)
        self.statement = connection.createStatement()
        self.userSelect = getUserSelect(connection)
        self.userInsert = getUserInsert(connection)
        self.itemSelect = getItemSelect(connection)
        self.itemInsert = getItemInsert(connection)
        self.itemUpdate = getItemUpdate(connection)
        self.childDelete = getChildDelete(connection)
        self.childInsert = getChildInsert(connection)
        self.idInsert = getIdInsert(connection)
        self.idSelect = getIdSelect(connection)
        self.idUpdate = getIdUpdate(connection)

    def _shutdownDataBase(self):
        self.userSelect.close()
        self.userInsert.close()
        self.itemSelect.close()
        self.itemInsert.close()
        self.itemUpdate.close()
        self.childDelete.close()
        self.childInsert.close()
        self.idInsert.close()
        self.idSelect.close()
        self.idUpdate.close()
        self.statement.execute('SHUTDOWN COMPACT;')

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
