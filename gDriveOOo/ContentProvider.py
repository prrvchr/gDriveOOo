#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo, XComponent
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory, IllegalIdentifierException
from com.sun.star.beans import XPropertiesChangeListener
from com.sun.star.frame import XTerminateListener, TerminationVetoException

import traceback

from gdrive import ContentIdentifier
from gdrive import getDbConnection, getUserSelect, getUserInsert, executeUserInsert, executeUpdateInsertItem
from gdrive import getItemSelect, getItemInsert, getItemUpdate, getContentProperties
from gdrive import executeItemInsert, getChildDelete, getChildInsert

from gdrive import createService, getItem, getUri, getUriPath, getProperty
from gdrive import getLogger, insertContent, updateContent
from gdrive import getNewId, getId, getIdSelect, getIdInsert, getIdUpdate

from requests import codes

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider'

g_Scheme = 'vnd.google-apps'


class ContentProvider(unohelper.Base, XComponent, XServiceInfo, XContentProvider,
                      XContentIdentifierFactory, XPropertiesChangeListener, XTerminateListener):
    def __init__(self, ctx):
        try:
            print("ContentProvider.__init__()")
            self.ctx = ctx
            self.Logger = getLogger(self.ctx)
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            msg = "ContentProvider for Scheme: %s loading ..." % g_Scheme
            self.Logger.logp(level, "ContentProvider", "__init__()", msg)
            self.UserName = None
            self.Root = {}
            self.listener = []
            self._initDataBase()
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            msg = "ContentProvider for Scheme: %s loading ... Done" % g_Scheme
            self.Logger.logp(level, "ContentProvider", "__init__()", msg)
            print("ContentProvider.__init__()")
        except Exception as e:
            print("ContentProvider.__init__().Error: %s" % e)

    @property
    def RootId(self):
        return self.Root['Id'] if 'Id' in self.Root else ''
    @RootId.setter
    def RootId(self, id):
        pass

    # XTerminateListener
    def queryTermination(self, event):
        print("ContentProvider.queryTermination()")
        # ToDo: Upload modified metadata/files after asking user
    def notifyTermination(self, event):
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
        msg = "Shutdown database ..."
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", msg)
        msg = "Shutdown database ... connection alredy closed..."
        connection = self.statement.getConnection()
        if not connection.isClosed():
            self._shutdownDataBase(connection)
            msg = "Shutdown database ... Done"
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", msg)
        print("ContentProvider.notifyTermination() %s" % msg)

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

    # XPropertiesChangeListener
    def propertiesChange(self, events):
        for event in events:
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            if event.PropertyName == 'Id':
                msg = "Item inserted new Id: %s ..." % event.NewValue
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
                if insertContent(self.ctx, event, self.itemInsert, self.childInsert, self.idUpdate, self.RootId):
                    msg = "Item inserted new Id: %s ... Done" % event.NewValue
                else:
                    level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
                    msg = "ERROR: Can't insert new Id: %s" % event.NewValue
            else:
                msg = "Item updated Property: %s ..." % event.PropertyName
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
                if updateContent(event, self.statement):
                    msg = "Item updated Property: %s ... Done" % event.PropertyName
                else:
                    level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
                    msg = "ERROR: Can't update Property: %s" % event.PropertyName
                self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
    def disposing(self, source):
        print("ContentProvider.disposing() %s" % (source, ))

    # XContentIdentifierFactory
    def createContentIdentifier(self, identifier):
        print("ContentProvider.createContentIdentifier()")
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
        msg = "Identifier: %s ..." % identifier
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        uri = getUri(self.ctx, identifier)
        if not self._checkAuthority(uri):
            raise IllegalIdentifierException('Identifier has no Authority: %s' % identifier, self)
        id = getId(uri, self.RootId)
        if id == 'new':
            msg = "New Identifier: %s ..." % uri.getUriReference()
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
            id = getNewId(self.ctx, g_Scheme, self.UserName, self.idSelect, self.idInsert)
            path = getUriPath(uri, id, True)
            identifier = '%s://%s/%s' % (g_Scheme, uri.getAuthority(), '/'.join(path))
            uri = getUri(self.ctx, identifier)
            msg = "New Identifier: %s ... DONE" % uri.getUriReference()
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)           
        msg = "Identifier: %s ... Done" % uri.getUriReference()
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        return ContentIdentifier(uri)

    # XParameterizedContentProvider
    def registerInstance(self, template, argument, replace):
        print("ContentProvider.registerInstance() ****************************************")
    def deregisterInstance(self, template, argument):
        print("ContentProvider.deregisterInstance() ****************************************")

    # XContentProvider
    def queryContent(self, identifier):
        identifier = identifier.getContentIdentifier()
        print("ContentProvider.queryContent() 1: %s" % identifier)
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
        msg = "Identifier: %s..." % identifier
        self.Logger.logp(level, "ContentProvider", "queryContent()", msg)
        uri = getUri(self.ctx, identifier)
        print("ContentProvider.queryContent() 2: %s" % uri.getUriReference())
        if not self._checkAuthority(uri):
            raise IllegalIdentifierException('Identifier has no Authority: %s' % identifier, self)
        print("ContentProvider.queryContent() 3: %s" % (self.RootId, ))
        id = getId(uri, self.RootId)
        print("ContentProvider.queryContent() 4: %s - %s" % (id, self.RootId))
        if id == '':
            raise IllegalIdentifierException('Identifier has illegal Path: %s' % identifier, self)
        retrived, item = self._getItem(id)
        if not retrived:
            raise IllegalIdentifierException('Identifier has not been retrived: %s' % id, self)
        item.update({'Uri': uri})
        name = 'com.gmail.prrvchr.extensions.gDriveOOo.'
        media = item['MediaType']
        if media == 'application/vnd.google-apps.folder':
            statements = {'itemUpdate': self.itemUpdate, 'itemInsert': self.itemInsert,
                         'childDelete': self.childDelete, 'childInsert': self.childInsert}
            item.update(statements)
            name += 'DriveFolderContent' if id != self.RootId else 'DriveRootContent'
        elif media.startswith('application/vnd.oasis.opendocument'):
            name += 'DriveOfficeContent'
        else:
            raise IllegalIdentifierException('ContentType is unknown: %s' % media, self)
        service = createService(name, self.ctx, **item)
        service.addPropertiesChangeListener(('IsInCache', 'Title', 'Size'), self)
        msg = "Identifier: %s... Done" % identifier
        self.Logger.logp(level, "ContentProvider", "queryContent()", msg)
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

    def _checkAuthority(self, uri):
        if uri.hasAuthority() and self.UserName != uri.getAuthority():
            return self._getUserName(uri.getAuthority())
        elif self.UserName is not None:
            return True
        return False

    def _getUserName(self, username):
        try:
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            msg = "UserName have been changed ..."
            self.Logger.logp(level, "ContentProvider", "_getUserName()", msg)
            self.userSelect.setString(1, username)
            result = self.userSelect.executeQuery()
            if result.next():
                retrived, self.UserName, self.Root = self._getUserFromDataBase(result, username)
                level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
                msg = "UserName retreive from database ... Done"
                self.Logger.logp(level, "ContentProvider", "_getUserFromDataBase()", msg)
            else:
                retrived, self.UserName, self.Root = self._getUserFromProvider(username)
            result.close()
            return retrived
        except Exception as e:
            print("ContentProvider._getUserName().Error: %s - %s" % (e, traceback.print_exc()))

    def _getUserFromDataBase(self, result, username):
        root = self._getItemFromResult(result, username)
        return True, username, root

    def _getUserFromProvider(self, username):
        retrived = False
        root = {}
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
        msg = None
        status, json = getItem(self.ctx, g_Scheme, username, 'root')
        if status is None:
            msg = "ERROR: Can't retreive from provider UserName: %s" % username
        elif status == codes.ok:
            if executeUserInsert(self.userInsert, username, json['id']) and \
               executeUpdateInsertItem(self.itemUpdate, self.itemInsert, json):
                result = self.userSelect.executeQuery()
                if result.next():
                    retrived, username, root = self._getUserFromDataBase(result, username)
                    level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
                    msg = "UserName retreive from provider ... Done"
                result.close()
            else:
                msg = "ERROR: Can't insert new User in databse UserName: %s" % username
        elif status == codes.bad_request:
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        if msg is not None:
            self.Logger.logp(level, "ContentProvider", "_getUserFromProvider()", msg)
        return retrived, username, root

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
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
        msg = None
        status, json = getItem(self.ctx, g_Scheme, self.UserName, id)
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
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
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
            else:
                print("ContentProvider._getItemFromResult() Error ***************************************Error")
            if result.wasNull():
                value = None
            print("ContentProvider._getItemFromResult() %s - %s" % (result.MetaData.getColumnName(index), value))
            item[result.MetaData.getColumnName(index)] = value
        return item

    def _initDataBase(self):
        desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
        desktop.addTerminateListener(self)
        connection = getDbConnection(self.ctx, g_Scheme)
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

    def _shutdownDataBase(self, connection):
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
