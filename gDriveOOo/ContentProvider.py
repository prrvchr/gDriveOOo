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

from gdrive import ContentIdentifier, InteractionRequest
from gdrive import getDbConnection, selectRoot, mergeRoot, selectItem, insertItem
from gdrive import getItem, mergeContent, checkIdentifiers, getIdentifier

from gdrive import getUcb, setContentProperties
from gdrive import createService, getUri, getProperty, g_folder, getSession
from gdrive import getLogger, getPropertyValue, getUser, isIdentifier, getConnectionMode

from requests import Session, codes
import traceback

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
        self.Session = None
        self._UserName = ''
        self._Root = {}
        self.cachedContent = {}
        self.Logger = getLogger(self.ctx)
        self.ConnectionMode = getConnectionMode(self.ctx)
        print("ContentProvider.__init__() %s" % self.ConnectionMode)
        msg += " Done"
        desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
        desktop.addTerminateListener(self)
        self.Logger.logp(level, "ContentProvider", "__init__()", msg)

    @property
    def Root(self):
        return self._Root
    @Root.setter
    def Root(self, root):
        if self.UserId != root['UserId']:
            self._Root = root
            checkIdentifiers(self.Statement.getConnection(), self.Session, self.UserId)
    @property
    def RootId(self):
        return self.Root['Id'] if 'Id' in self.Root else ''
    @property
    def UserId(self):
        return self.Root['UserId'] if 'UserId' in self.Root else ''
    @property
    def UserName(self):
        return self.Root['UserName'] if 'UserName' in self.Root else None

    # XParameterizedContentProvider
    def registerInstance(self, template, arguments, replace):
        self.Scheme = template
        # Piggyback DataBase Connections (easy and clean ShutDown ;-) )
        self.Statement = getDbConnection(self.ctx, self.Scheme, True).createStatement()
        return getUcb(self.ctx).registerContentProvider(self, self.Scheme, replace)
    def deregisterInstance(self, template, argument):
        getUcb(self.ctx).deregisterContentProvider(self, self.Scheme)

    # XTerminateListener
    def queryTermination(self, event):
        # ToDo: Upload modified metadata/files after asking user
        pass
    def notifyTermination(self, event):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", "Shutdown database ...")
        if self.Statement and not self.Statement.getConnection().isClosed():
            self.Statement.execute('SHUTDOWN COMPACT;')
            msg = "Shutdown database ... closing connection ... Done"
        else:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = "Shutdown database ... connection alredy closed !!!"
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", msg)

    # XPropertiesChangeListener
    def propertiesChange(self, events):
        for event in events:
            name = event.PropertyName
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "Item inserted new Id: %s ..." % event.NewValue if name == 'Id' else \
                  "Item updated Property: %s ..." % name
            self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
            if mergeContent(self.ctx, self.Statement.getConnection(), event, self.UserId):
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
        if uri is None:
            raise IllegalIdentifierException('Identifier cannot be parsed: %s' % identifier, self)
        if not self._hasUserName(uri):
            raise IllegalIdentifierException('Identifier need a UserName: %s' % identifier, self)
        if uri.hasFragment():
            msg = "New Identifier: %s ..." % identifier
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
            uri.clearFragment()
            baseuri = uri.getUriReference()
            id = getIdentifier(self.Statement.getConnection(), self.UserId)
            print("ContentProvider.createContentIdentifier() createNewId %s" % id)
            newidentifier = '%s%s' % (baseuri, id) if baseuri.endswith('/') else '%s/%s' % (baseuri, id)
            uri = getUri(self.ctx, newidentifier)
            print("ContentProvider.createContentIdentifier() isIdentifier ******* %s" % (newidentifier, ))
        contentidentifier = ContentIdentifier(self.ctx, self.ConnectionMode, uri, self.UserId, self.UserName, self.RootId)
        msg = "Identifier: %s ... Done" % contentidentifier.getContentIdentifier()
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        return contentidentifier

    # XContentProvider
    def queryContent(self, identifier):
        print("ContentProvider.queryContent() %s" % identifier.getContentIdentifier())
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifier: %s..." % identifier
        if not isIdentifier(self.Statement.getConnection(), identifier):
            raise IllegalIdentifierException('Identifier has illegal Path: %s' % identifier.getContentIdentifier(), self)
        ret, content = self._getContent(identifier)
        if not ret:
            raise IllegalIdentifierException('Identifier has not been retrived: %s' % identifier.getContentIdentifier(), self)
        msg += " Done"
        self.Logger.logp(level, "ContentProvider", "queryContent()", msg)
        return content

    def compareContentIds(self, identifier1, identifier2):
        compare = 1
        print("ContentProvider.compareContentIds() %s - %s" % (identifier1.getContentIdentifier(), identifier2.getContentIdentifier()))
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifiers: %s - %s ..." % (identifier1.getContentIdentifier(), identifier2.getContentIdentifier())
        if identifier1.Id == identifier2.Id:
            msg += " seem to be the same..."
            compare = 0
        elif identifier1.Uri.getPathSegmentCount() != identifier2.Uri.getPathSegmentCount():
            msg += " are not the same..."
            compare = identifier1.Uri.getPathSegmentCount() - identifier2.Uri.getPathSegmentCount()
        else:
            msg += " are not the same..."
        msg += " Done"
        self.Logger.logp(level, "ContentProvider", "compareContentIds()", msg)
        return compare

    # XInteractionSupplyParameters
    def setParameters(self, values):
        for property in values:
            if property.Name == 'UserName' and property.Value:
                self._UserName = property.Value
    def select(self):
        pass

    def _hasUserName(self, uri):
        username = ''
        if uri.hasAuthority() and uri.getAuthority() != '' and uri.getAuthority() != self.UserName:
            username = uri.getAuthority()
            print("ContentProvider._hasUserName() %s" % username)
        elif self.UserName is None:
            username = self._getUserFromHandler()
            print("ContentProvider._hasUserName() %s" % username)
        else:
            return True
        return self._getUser(username) if username else False

    def _getUserFromHandler(self):
        self._UserName = ''
        message = "Authentication is needed!!!"
        window = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop').ActiveFrame.ComponentWindow
        args = (getPropertyValue('Parent', window), getPropertyValue('Context', message))
        interaction = self.ctx.ServiceManager.createInstanceWithArguments('com.sun.star.task.InteractionHandler', args)
        ret = interaction.handleInteractionRequest(InteractionRequest(self, self.Statement.getConnection(), message))
        return self._UserName

    def _getUser(self, username):
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
            print("ContentProvider._getUser(): %s" % root)
            self.Root = root
        return ret

    def _getRoot(self, username):
        ret, root, self.Session = False, {}, getSession(self.ctx, self.Scheme, username)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        msg = None
        status1, user = getUser(self.Session)
        status2, item = getItem(self.Session, 'root')
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

    def _getItem(self, id):
        ret, item = False, {}
        msg = None
        status, json = getItem(self.Session, id)
        if status == codes.ok:
            ret, item = insertItem(self.Statement.getConnection(), self.UserId, json)
        elif status == codes.bad_request:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        else:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = "ERROR: Can't retreive Id from provider: %s" % id
        if msg is not None:
            self.Logger.logp(level, "ContentProvider", "_getItem()", msg)            
        return ret, item

    def _getContent(self, identifier):
        ret = identifier.Id in self.cachedContent
        if ret:
            content = self.cachedContent[identifier.Id]
            # Same Content can have multiple parent...
            setContentProperties(content, {'Identifier': identifier})
        elif identifier.Name is None:
            ret, content = self._createContent(identifier)
        else:
            ret, content = self._createNewContent(identifier)
        return ret, content

    def _createContent(self, identifier):
        id, content = identifier.Id, None
        ret, item = selectItem(self.Statement.getConnection(), self.UserId, id)
        if not ret and self.ConnectionMode == ONLINE:
            ret, item = self._getItem(id)
        if ret:
            name = None
            item.update({'Identifier': identifier})
            media = item['MediaType']
            if media == g_folder:
                name = 'DriveRootContent' if identifier.IsRoot else 'DriveFolderContent'
                item.update({'Statement': self.Statement})
            else:
                name = 'DriveOfficeContent'
            if name:
                service = 'com.gmail.prrvchr.extensions.gDriveOOo.%s' % name
                content = createService(service, self.ctx, **item)
                content.addPropertiesChangeListener(('IsWrite', 'ConnectionMode', 'Name', 'Size'), self)
                self.cachedContent[id] = content
        return ret, content

    def _createNewContent(self, identifier):
        item = {'Name': identifier.Name, 'Identifier': identifier}
        content = createService('com.gmail.prrvchr.extensions.gDriveOOo.DriveOfficeContent', self.ctx, **item)
        content.addPropertiesChangeListener(('IsWrite', 'ConnectionMode', 'Name', 'Size'), self)
        self.cachedContent[identifier.Id] = content
        return True, content

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
