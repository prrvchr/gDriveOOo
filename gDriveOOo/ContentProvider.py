#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContentProvider, XContentIdentifierFactory
from com.sun.star.ucb import XParameterizedContentProvider
from com.sun.star.ucb import ContentCreationException, IllegalIdentifierException
from com.sun.star.ucb import InteractiveNetworkOffLineException
from com.sun.star.auth import AuthenticationFailedException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
from com.sun.star.beans import XPropertiesChangeListener
from com.sun.star.frame import XTerminateListener, TerminationVetoException

from gdrive import ContentIdentifier, InteractionRequestParameters, PropertySet
from gdrive import getDbConnection, selectUser, mergeJsonUser, selectItem, insertJsonItem
from gdrive import getItem, updateContent, checkIdentifiers, getNewIdentifier
from gdrive import getUcb, ContentUser, createContent, getInteractionHandler
from gdrive import createService, getUri, getProperty, getSession, getIllegalIdentifierException
from gdrive import getInteractiveNetworkOffLineException, getInteractiveNetworkReadException
from gdrive import g_scheme
from gdrive import getLogger, getPropertyValue, getUser, isIdentifier, getConnectionMode

from requests import Session
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider'


class ContentProvider(unohelper.Base, XServiceInfo, XContentIdentifierFactory, PropertySet,
                      XContentProvider, XPropertiesChangeListener, XParameterizedContentProvider,
                      XTerminateListener):
    def __init__(self, ctx):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "ContentProvider loading ..."
        self.ctx = ctx
        self._Statement = None
        self._User = ContentUser(ctx)
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
        self._User = user
        if self.User.IsValid and self.Mode == ONLINE:
            checkIdentifiers(self.Connection, self.User)
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
            if updateContent(self.ctx, event, self.Mode):
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
        try:
            print("ContentProvider.createContentIdentifier() 1 %s" % identifier)
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "Identifier: %s ..." % identifier
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
            uri = getUri(self.ctx, identifier)
            print("ContentProvider.createContentIdentifier() 2 %s" % identifier)
            self._setUser(uri)
            contentidentifier = ContentIdentifier(self.ctx, self.Connection, self.Mode, self.User, uri)
            msg = "Identifier: %s ... Done" % contentidentifier.getContentIdentifier()
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
            return contentidentifier
        except Exception as e:
            print("ContentProvider.createContentIdentifier().Error: %s - %e" % (e, traceback.print_exc()))

    # XContentProvider
    def queryContent(self, identifier):
        error, content = identifier.User.Error, None
        print("ContentProvider.queryContent() 1 %s" % identifier.getContentIdentifier())
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        msg = "Identifier: %s..." % identifier.getContentIdentifier()
        print("ContentProvider.queryContent() 2 %s" % error)
        if identifier.IsValid:
            print("ContentProvider.queryContent() 3 %s" % identifier.getContentIdentifier())
            content = self._getCachedContent(identifier)
        if error is not None:
            print("ContentProvider.queryContent() 4 %s" % identifier.getContentIdentifier())
            self.Logger.logp(level, "ContentProvider", "queryContent()", "%s - %s" % (msg, error.Message))
            print("ContentProvider.queryContent() %s - %s" % (msg, error.Message))
            raise error
        if content is None:
            e = ContentCreationException()
            e.eError = uno.Enum('com.sun.star.ucb.ContentCreationError', 'CONTENT_CREATION_FAILED')
            e.Message = "Identifier has not been retrieved: %s" % identifier.getContentIdentifier()
            e.Context = self
            raise e
        msg += " Done"
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
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

    def _setUser(self, uri):
        if uri.hasAuthority() and uri.getAuthority() != '' and uri.getAuthority() != self.User.Name:
            username = uri.getAuthority()
        elif self.User.Name is None:
            username = self._getUserFromHandler()
        else:
            return
        scheme = uri.getScheme()
        user = self._getUser(scheme, username)
        self.User = ContentUser(self.ctx, scheme, user)

    def _getUserFromHandler(self):
        result = {}
        message = "Authentication is needed!!!"
        interaction = getInteractionHandler(self.ctx, message)
        request = InteractionRequestParameters(self, self.Connection, message, result)
        if interaction.handleInteractionRequest(request):
            if result.get('Retrieved', False):
                return result.get('UserName')
        return None

    def _getUser(self, scheme, username):
        if username is None:
            message = "ERROR: Can't retrieve a UserName from Handler"
            user = {'Error': AuthenticationFailedException(message, self)}
            return user
        user = selectUser(self.Connection, username, self.Mode)
        if user is None:
            if self.Mode == OFFLINE:
                self.Mode = ONLINE
            if self.Mode == ONLINE:
                user = self._getUserFromProvider(scheme, username)
            else:
                message = "ERROR: Can't retrieve User: %s Network is Offline" % username
                user = {'Error': getInteractiveNetworkOffLineException(self, message)}
        return user

    def _getUserFromProvider(self, scheme, username):
        with getSession(self.ctx, scheme, username) as session:
            data, root = getUser(session)
        print("ContentProvider._getUserFromProvider(): %s" % username)
        if root is not None:
            user = mergeJsonUser(self.Connection, data, root, self.Mode)
        else:
            message = "ERROR: Can't retrieve User: %s from provider" % username
            user = {'Error': getInteractiveNetworkReadException(self, message)}
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            self.Logger.logp(level, "ContentProvider", "_getUser()", message)
        return user

    def _getItem(self, identifier):
        item = None
        with identifier.User.Session as session:
            data = getItem(session, identifier.Id)
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
        #content.addContentEventListener(self)
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
