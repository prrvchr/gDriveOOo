#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory
from com.sun.star.ucb import XParameterizedContentProvider, IllegalIdentifierException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
from com.sun.star.beans import XPropertiesChangeListener
from com.sun.star.frame import XTerminateListener, TerminationVetoException
from com.sun.star.sdb import XInteractionSupplyParameters

import traceback

from gdrive import ContentIdentifier, InteractionRequest
from gdrive import getDbConnection, selectRoot, mergeRoot, selectItem, insertItem
from gdrive import getItem, mergeContent, checkIdentifiers, geIdentifier

from gdrive import getUcb, getContentProperties, setContentProperties
from gdrive import createService, getUri, getUriPath, getProperty
from gdrive import getLogger, getParentUri, getId, getPropertyValue, getUser

from requests import codes

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider'


class ContentProvider(unohelper.Base, XServiceInfo, XContentIdentifierFactory,
                      XContentProvider, XPropertiesChangeListener, XParameterizedContentProvider,
                      XTerminateListener, XInteractionSupplyParameters):
    def __init__(self, ctx):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "ContentProvider loading ..."
        self.ctx = ctx
        self.Scheme = None          #'vnd.google-apps'
        self.Statement = None
        self.ConnectionMode = ONLINE
        self.Parameter = None
        self._Root = {}
        self.currentFolder = None
        self.listeners = []
        self.cachedContent = {}
        self.Logger = getLogger(self.ctx)
        msg += " Done"
        desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
        desktop.addTerminateListener(self)
        self.Logger.logp(level, "ContentProvider", "__init__()", msg)

    @property
    def Root(self):
        return self._Root
    @Root.setter
    def Root(self, root):
        username = root['UserName']
        if self.UserName != username:
            checkIdentifiers(self.ctx, self.Scheme, self.Statement.getConnection(), username)
        self._Root = root
    @property
    def RootId(self):
        return self.Root['Id'] if 'Id' in self.Root else ''
    @property
    def RootUri(self):
        return self.Root['Uri'] if 'Uri' in self.Root else getUri(self.ctx, '%s://%s/' % (self.Scheme, self.UserName))
    @property
    def UserId(self):
        return self.Root['UserId'] if 'UserId' in self.Root else ''
    @property
    def UserName(self):
        return self.Root['UserName'] if 'UserName' in self.Root else None

    # XParameterizedContentProvider
    def registerInstance(self, template, arguments, replace):
        self.Scheme = template
        # Piggyback DataBase Connections (easy and clean ShutDown ;.) )
        self.Statement = getDbConnection(self.ctx, self.Scheme, True).createStatement()
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
        if not self.Statement.getConnection().isClosed():
            #self.Statement.getConnection().close()
            self.Statement.execute('SHUTDOWN COMPACT;')
            print("ContentProvider.notifyTermination() 2")
            msg += "closing connection ..."
        else:
            print("ContentProvider.notifyTermination() 3")
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg += " connection alredy closed !!!"
        msg += " Done"
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", msg)
        print("ContentProvider.notifyTermination() 4")

    # XPropertiesChangeListener
    def propertiesChange(self, events):
        for event in events:
            name = event.PropertyName
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "Item inserted new Id: %s ..." % event.NewValue if name == 'Id' else \
                  "Item updated Property: %s ..." % name
            self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
            if mergeContent(self.ctx, self.Statement.getConnection(), event, self.RootId, self.UserId):
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
            id = geIdentifier(self.Statement.getConnection(), self.UserName)
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
            ret, content = self._getContent(id, uri)
            if not ret:
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

    # XInteractionSupplyParameters
    def setParameters(self, values):
        for property in values:
            if property.Name == 'UserName' and property.Value:
                self.Parameter = property.Value
    def select(self):
        pass

    def _checkAuthority(self, uri):
        if uri.hasAuthority() and uri.getAuthority() != '' and uri.getAuthority() != self.UserName:
            return self._getUser(uri.getAuthority())
        elif self.UserName is None:
            self.Parameter = None
            message = "Authentication is needed!!!"
            window = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop').ActiveFrame.ComponentWindow
            args = (getPropertyValue('Parent', window), getPropertyValue('Context', message))
            interaction = self.ctx.ServiceManager.createInstanceWithArguments('com.sun.star.task.InteractionHandler', args)
            interaction.handle(InteractionRequest(self, self.Statement.getConnection(), message))
            return False if self.Parameter is None else self._getUser(self.Parameter)
        return True

    def _getUser(self, username):
        try:
            self.Parameter = None
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "UserName have been changed ..."
            self.Logger.logp(level, "ContentProvider", "_getUserName()", msg)
            ret, root = selectRoot(self.Statement.getConnection(), username)
            if ret:
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
                msg = "UserName retreive from database ... Done"
                self.Logger.logp(level, "ContentProvider", "_getUserName()", msg)
            elif self.ConnectionMode == ONLINE:
                ret, root = self._getRoot(username)
            if ret:
                self.Root = root
            return ret
        except Exception as e:
            print("ContentProvider._getUserName().Error: %s - %s" % (e, traceback.print_exc()))

    def _getRoot(self, username):
        try:
            ret, root = False, {}
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = None
            status1, user = getUser(self.ctx, self.Scheme, username)
            status2, item = getItem(self.ctx, self.Scheme, username, 'root')
            print("ContentProvider._getUserFromProvider(): %s" % username)
            if status1 == codes.ok and status2 == codes.ok:
                ret, root = mergeRoot(self.Statement.getConnection(), user, item)
            elif status1 == codes.bad_request and status2 == codes.bad_request:
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
                msg = "ERROR: Can't retreive Id from provider: %s" % id
            else:
                msg = "ERROR: Can't retreive from provider UserName: %s" % username
            if msg is not None:
                self.Logger.logp(level, "ContentProvider", "_getUser()", msg)
            return ret, root
        except Exception as e:
            print("ContentProvider._getUser().Error: %s - %s" % (e, traceback.print_exc()))

    def _getItem(self, id):
        ret, item = False, {}
        msg = None
        status, json = getItem(self.ctx, self.Scheme, self.UserName, id)
        if status == codes.ok:
            ret, item = insertItem(self.Statement.getConnection(), json)
        elif status == codes.bad_request:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        else:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        if msg is not None:
            self.Logger.logp(level, "ContentProvider", "_getItem()", msg)            
        return ret, item

    def _getContent(self, id, uri):
        ret = id in self.cachedContent
        if ret:
            content = self.cachedContent[id]
            # a Content can have multiple parent...
            setContentProperties(content, {'UserName': self.UserName, 'Uri': uri, 'ConnectionMode': self.ConnectionMode})
        else:
            ret, content = self._createContent(id, uri)
        return ret, content

    def _createContent(self, id, uri):
        content = None
        ret, item = selectItem(self.Statement.getConnection(), id)
        if not ret and self.ConnectionMode == ONLINE:
            ret, item = self._getItem(id)
        if ret:
            name = None
            item.update({'UserName': self.UserName, 'Uri': uri, 'ConnectionMode': self.ConnectionMode})
            media = item['MediaType']
            if media == 'application/vnd.google-apps.folder':
                name = 'DriveFolderContent' if id != self.RootId else 'DriveRootContent'
                item.update({'Statement': self.Statement})
            elif media.startswith('application/vnd.oasis.opendocument'):
                name = 'DriveOfficeContent'
            if name:
                service = 'com.gmail.prrvchr.extensions.gDriveOOo.%s' % name
                content = createService(service, self.ctx, **item)
                content.addPropertiesChangeListener(('WhoWrite', 'IsRead', 'Name', 'Size'), self)
                self.cachedContent[id] = content
        return ret, content

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
