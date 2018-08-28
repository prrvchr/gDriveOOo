#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo, XComponent
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory, XParameterizedContentProvider
from com.sun.star.ucb import URLAuthenticationRequest, IllegalIdentifierException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
from com.sun.star.beans import XPropertiesChangeListener
from com.sun.star.frame import XTerminateListener, TerminationVetoException

import traceback

from gdrive import ContentIdentifier
from gdrive import getDbConnection, selectRoot, mergeRoot, selectItem, insertItem
from gdrive import getItem, mergeContent

from gdrive import getUcb, getContentProperties, setContentProperties
from gdrive import createService, getUri, getUriPath, getProperty
from gdrive import getLogger, getParentUri, getNewId, getId
from gdrive import getIdSelect, getIdInsert, getIdUpdate

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
        self.Connection = None
        self.ConnectionMode = ONLINE
        self.UserName = None
        self.Root = {}
        self.currentFolder = None
        self.listeners = []
        self.cachedContent = {}
        self.Logger = getLogger(self.ctx)
        msg += " Done"
        desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
        desktop.addTerminateListener(self)
        self.Logger.logp(level, "ContentProvider", "__init__()", msg)

    @property
    def RootId(self):
        return self.Root['Id'] if 'Id' in self.Root else ''
    @property
    def RootUri(self):
        return self.Root['Uri'] if 'Uri' in self.Root else getUri(self.ctx, '%s://%s/' % (self.Scheme, self.UserName))

    # XParameterizedContentProvider
    def registerInstance(self, template, arguments, replace):
        self.Scheme = template
        self.Connection = getDbConnection(self.ctx, self.Scheme)
        self.statement = self.Connection.createStatement()
        self.idInsert = getIdInsert(self.Connection)
        self.idSelect = getIdSelect(self.Connection)
        self.idUpdate = getIdUpdate(self.Connection)
        return getUcb(self.ctx).registerContentProvider(self, self.Scheme, replace)
    def deregisterInstance(self, template, argument):
        getUcb(self.ctx).deregisterContentProvider(self, self.Scheme)

    # XTerminateListener
    def queryTermination(self, event):
        # ToDo: Upload modified metadata/files after asking user
        pass
    def notifyTermination(self, event):
        print("ContentProvider.notifyTermination() 1")
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Shutdown database ..."
        if self.Connection.isClosed():
            print("ContentProvider.notifyTermination() 2")
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg += " connection alredy closed !!!"
        else:
            self.idInsert.close()
            self.idSelect.close()
            self.idUpdate.close()
            #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
            #connection = getDbConnection(self.ctx, 'vnd.google-apps')
            #mri.inspect(self.Connection)
            self.Connection.close()
            print("ContentProvider.notifyTermination() 3")
            msg += "closing connection ..."
        msg += " Done"
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", msg)
        print("ContentProvider.notifyTermination() 4")

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
            name = event.PropertyName
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "Item inserted new Id: %s ..." % event.NewValue if name == 'Id' else \
                  "Item updated Property: %s ..." % name
            self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
            if mergeContent(self.ctx, self.Connection, event, self.RootId):
                msg = "Item inserted new Id: %s ... Done" % event.NewValue if name == 'Id' else \
                      "Item updated Property: %s ... Done" % event.PropertyName
            else:
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                msg = "ERROR: Can't insert new Id: %s" % event.NewValue if name == 'Id' else \
                      "ERROR: Can't update Property: %s" % name
            self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
    def disposing(self, source):
        pass

    # XContentIdentifierFactory
    def createContentIdentifier(self, identifier):
        print("ContentProvider.createContentIdentifier() %s" % identifier)
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
        try:
            identifier = identifier.getContentIdentifier()
            print("ContentProvider.queryContent() %s" % identifier)
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "Identifier: %s..." % identifier
            uri = getUri(self.ctx, identifier)
            if not self._checkAuthority(uri):
                raise IllegalIdentifierException('Identifier has no Authority: %s' % identifier, self)
            id = getId(uri, self.RootId)
            if len(id) < 16:
                raise IllegalIdentifierException('Identifier has illegal Path: %s' % identifier, self)
            retrived, content = self._getContent(id, uri)
            if not retrived:
                raise IllegalIdentifierException('Identifier has not been retrived: %s' % id, self)
            if not getContentProperties(content, ('IsFolder', )).getBoolean(1):
                self.currentFolder = getParentUri(self.ctx, uri)
            msg += " Done"
            self.Logger.logp(level, "ContentProvider", "queryContent()", msg)
            return content
        except Exception as e:
            print("ContentProvider._getUserFromProvider().Error: %s - %s" % (e, traceback.print_exc()))

    def compareContentIds(self, identifier1, identifier2):
        compare = 1
        identifier1 = identifier1.getContentIdentifier()
        identifier2 = identifier2.getContentIdentifier()
        print("ContentProvider.compareContentIds() %s - %s" % (identifier1, identifier2))
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
        try:
            retrived = False
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "UserName have been changed ..."
            self.Logger.logp(level, "ContentProvider", "_getUserName()", msg)
            retrived, self.UserName, self.Root = selectRoot(self.Connection, username)
            if retrived:
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
                msg = "UserName retreive from database ... Done"
                self.Logger.logp(level, "ContentProvider", "_getUserName()", msg)
            elif self.ConnectionMode == ONLINE:
                retrived, self.UserName, self.Root = self._getUserFromProvider(username)
            return retrived
        except Exception as e:
            print("ContentProvider._getUserName().Error: %s - %s" % (e, traceback.print_exc()))

    def _getUserFromProvider(self, username):
        try:
            retrived, root = False, {}
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = None
            status, root = getItem(self.ctx, self.Scheme, username, 'root')
            print("ContentProvider._getUserFromProvider(): %s" % username)
            if status == codes.ok:
                retrived, root = mergeRoot(self.Connection, username, root)
            elif status == codes.bad_request:
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
                msg = "ERROR: Can't retreive Id from provider: %s" % id
            else:
                msg = "ERROR: Can't retreive from provider UserName: %s" % username
            if msg is not None:
                self.Logger.logp(level, "ContentProvider", "_getUserFromProvider()", msg)
            return retrived, username, root
        except Exception as e:
            print("ContentProvider._getUserFromProvider().Error: %s - %s" % (e, traceback.print_exc()))

    def _getContent(self, id, uri):
        retrived = id in self.cachedContent
        if retrived:
            content = self.cachedContent[id]
            # a Content can have multiple parent...
            setContentProperties(content, {'UserName': self.UserName, 'Uri': uri, 'ConnectionMode': self.ConnectionMode})
        else:
            retrived, content = self._createContent(id, uri)
        return retrived, content

    def _createContent(self, id, uri):
        content = None
        retrived, item = selectItem(self.Connection, id)
        if not retrived and self.ConnectionMode == ONLINE:
            retrived, item = self._getItemFromProvider(id)
        if retrived:
            name = None
            item.update({'UserName': self.UserName, 'Uri': uri,
                         'ConnectionMode': self.ConnectionMode, 'statement': self.statement})
            media = item['MediaType']
            if media == 'application/vnd.google-apps.folder':
                name = 'DriveFolderContent' if id != self.RootId else 'DriveRootContent'
            elif media.startswith('application/vnd.oasis.opendocument'):
                name = 'DriveOfficeContent'
            if name:
                service = 'com.gmail.prrvchr.extensions.gDriveOOo.%s' % name
                content = createService(service, self.ctx, **item)
                content.addPropertiesChangeListener(('IsWrite', 'IsRead', 'Title', 'Size'), self)
                self.cachedContent[id] = content
        return retrived, content

    def _getItemFromProvider(self, id):
        retrived, item = False, {}
        msg = None
        status, json = getItem(self.ctx, self.Scheme, self.UserName, id)
        if status == codes.ok:
            retrived, item = insertItem(self.Connection, json)
        elif status == codes.bad_request:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        else:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        if msg is not None:
            self.Logger.logp(level, "ContentProvider", "_getItemFromProvider()", msg)            
        return retrived, item

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
