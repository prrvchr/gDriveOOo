#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory
from com.sun.star.ucb import XParameterizedContentProvider
from com.sun.star.ucb import ContentCreationException, IllegalIdentifierException
from com.sun.star.ucb import InteractiveNetworkOffLineException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
from com.sun.star.beans import XPropertiesChangeListener
from com.sun.star.frame import XTerminateListener, TerminationVetoException
from com.sun.star.sdb import XInteractionSupplyParameters

from gdrive import ContentIdentifier, InteractionRequest, PropertySet
from gdrive import getDbConnection, selectUser, mergeJsonUser, selectItem, insertJsonItem
from gdrive import getItem, mergeContent, checkIdentifiers, getNewIdentifier
from gdrive import getUcb, setContentProperties, ContentUser, createContent
from gdrive import createService, getUri, getProperty, getSession
from gdrive import g_scheme
from gdrive import getLogger, getPropertyValue, getUser, isIdentifier, getConnectionMode

from requests import Session
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider'


class ContentProvider(unohelper.Base, XServiceInfo, XContentIdentifierFactory, PropertySet,
                      XContentProvider, XPropertiesChangeListener, XParameterizedContentProvider,
                      XTerminateListener, XInteractionSupplyParameters):
    def __init__(self, ctx):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "ContentProvider loading ..."
        self.ctx = ctx
        self._Statement = None
        self.Session = None
        self._User = ContentUser()
        self._UserName = ''
        self.cachedContent = {}
        self.Logger = getLogger(self.ctx)
        self._Mode = getConnectionMode(self.ctx)
        print("ContentProvider.__init__() %s" % self.Mode)
        msg += " Done"
        desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
        desktop.addTerminateListener(self)
        self.Logger.logp(level, "ContentProvider", "__init__()", msg)

    def __del__(self):
        print("ContentProvider.__del__()***********************")

    @property
    def User(self):
        return self._User
    @User.setter
    def User(self, user):
        if self.User.Id != user.Id:
            self._User = user
            checkIdentifiers(self.Connection, self.Session, self.User.Id)
    @property
    def Mode(self):
        return self._Mode
    @Mode.setter
    def Mode(self, mode):
        if mode == getConnectionMode(self.ctx):
            self._Mode = mode
    @property
    def Connection(self):
        return self._Statement.getConnection()

    # XParameterizedContentProvider
    def registerInstance(self, template, arguments, replace):
        print("ContentProvider.registerInstance() 1 %s" % template)
        if g_scheme == template:
            print("ContentProvider.registerInstance() 2 %s - %s" % (g_scheme, template))
            # Piggyback DataBase Connections (easy and clean ShutDown ;-) )
            self._Statement = getDbConnection(self.ctx, g_scheme, True).createStatement()
            #self.Connection = getDbConnection(self.ctx, g_scheme, True)
            #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
            #mri.inspect(self.Connection)
            print("ContentProvider.registerInstance() 3")
            return getUcb(self.ctx).registerContentProvider(self, g_scheme, replace)
    def deregisterInstance(self, template, argument):
        getUcb(self.ctx).deregisterContentProvider(self, g_scheme)

    # XTerminateListener
    def queryTermination(self, event):
        # ToDo: Upload modified metadata/files after asking user
        pass
    def notifyTermination(self, event):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        self.Logger.logp(level, "ContentProvider", "notifyTermination()", "Shutdown database ...")
        if self._Statement and not self.Connection.isClosed():
            self._Statement.execute('SHUTDOWN;')
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
            if mergeContent(self.ctx, self.Connection, event, self.Mode):
                msg = "Item inserted new Id: %s ... Done" % event.OldValue if name == 'Id' else \
                      "Item updated Property: %s ... Done" % event.PropertyName
            else:
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                msg = "ERROR: Can't insert new Id: %s" % event.OldValue if name == 'Id' else \
                      "ERROR: Can't update Property: %s" % name
            self.Logger.logp(level, "ContentProvider", "propertiesChange()", msg)
    def disposing(self, source):
        pass

    # XContentIdentifierFactory
    def createContentIdentifier(self, identifier):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifier: %s ..." % identifier
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        uri = getUri(self.ctx, identifier)
        self._setUserName(uri)
        contentidentifier = ContentIdentifier(self.ctx, self.Connection, self.Mode, self.User, uri)
        msg = "Identifier: %s ... Done" % contentidentifier.getContentIdentifier()
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        return contentidentifier

    # XContentProvider
    def queryContent(self, identifier):
        message, content = None, None
        print("ContentProvider.queryContent() %s" % identifier.getContentIdentifier())
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifier: %s..." % identifier.getContentIdentifier()
        if identifier.IsValid:
            content = self._getCachedContent(identifier)
        elif not identifier.User.IsValid:
            message = "Identifier need a UserName: %s" % identifier.getContentIdentifier()
        else:
            message = "Identifier has illegal Path: %s" % identifier.getContentIdentifier()
        if message is not None:
            raise IllegalIdentifierException(message, self)
        if content is None:
            error = ContentCreationException()
            error.eError = uno.Enum('com.sun.star.ucb.ContentCreationError', 'CONTENT_CREATION_FAILED')
            error.Message = "Identifier has not been retrieved: %s" % identifier.getContentIdentifier()
            error.Context = self
            raise error
        msg += " Done"
        self.Logger.logp(level, "ContentProvider", "queryContent()", msg)
        return content

    def compareContentIds(self, identifier1, identifier2):
        compare = 1
        print("ContentProvider.compareContentIds() %s - %s" % (identifier1.getContentIdentifier(), identifier2.getContentIdentifier()))
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifiers: %s - %s ..." % (identifier1.getContentIdentifier(), identifier2.getContentIdentifier())
        if identifier1.getContentIdentifier() == identifier2.getContentIdentifier():
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

    def _setUserName(self, uri):
        if uri.hasAuthority() and uri.getAuthority() != '' and uri.getAuthority() != self.User.Name:
            self._setUser(uri.getAuthority())
        elif self.User.Name is None:
            self._setUser(self._getUserNameFromHandler())

    def _setUser(self, username):
        user = selectUser(self.Connection, username, self.Mode)
        if user is None and self.Mode == ONLINE:
            user = self._getUser(username)
        self.User = ContentUser(user)

    def _getUserNameFromHandler(self):
        self._UserName = ''
        message = "Authentication is needed!!!"
        window = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop').ActiveFrame.ComponentWindow
        args = (getPropertyValue('Parent', window), getPropertyValue('Context', message))
        interaction = self.ctx.ServiceManager.createInstanceWithArguments('com.sun.star.task.InteractionHandler', args)
        retrieved = interaction.handleInteractionRequest(InteractionRequest(self, self.Connection, message))
        return self._UserName

    def _getUser(self, username):
        user = None
        with getSession(self.ctx, username) as session:
            data, root = getUser(session)
            print("ContentProvider._getUserFromProvider(): %s" % username)
            if root is not None:
                user = mergeJsonUser(self.Connection, data, root, self.Mode)
                self.Session = session
            else:
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                msg = "ERROR: Can't retrieve User: %s from provider" % username
                self.Logger.logp(level, "ContentProvider", "_getUser()", msg)
        return user

    def _getItem(self, identifier):
        item = None
        data = getItem(self.Session, identifier.Id)
        if data is not None:
            item = insertJsonItem(self.Connection, identifier, data)
        else:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = "ERROR: Can't retrieve Id from provider: %s" % identifier.Id
            self.Logger.logp(level, "ContentProvider", "_getItem()", msg)            
        return item

    def _getCachedContent(self, identifier):
        key = identifier.getContentIdentifier()
        if key in self.cachedContent:
            content = self.cachedContent[key]
        else:
            content = self._getContent(identifier)
            if content is not None:
                self.cachedContent[key] = content
        return content

    def _getContent(self, identifier):
        content, item = None, selectItem(self.Connection, identifier.Id)
        if item is None and self.Mode == ONLINE:
            item = self._getItem(identifier)
        if item is None:
            return None
        data = item.get('Data', {})
        data.update({'Identifier': identifier})
        content = createContent(self.ctx, data)
        content.addPropertiesChangeListener(('Id', 'Name', 'Size', 'Trashed', 'Loaded', 'SyncMode'), self)
        return content

    # PropertySet
    def _getPropertySetInfo(self):
        properties = {}
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['Connection'] = getProperty('Connection', 'com.sun.star.sdbc.XConnection', maybevoid | readonly)
        properties['Mode'] = getProperty('Mode', 'short', bound)
        properties['User'] = getProperty('User', 'com.sun.star.uno.XInterface', maybevoid | bound)
        return properties

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
