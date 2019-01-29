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
from gdrive import getItem, mergeContent, checkIdentifiers, getIdentifier
from gdrive import getUcb, setContentProperties
from gdrive import createService, getUri, getProperty, getSession
from gdrive import g_scheme, g_folder, g_link, g_doc
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
        self._User = None
        self._UserName = ''
        self.cachedContent = {}
        self.Logger = getLogger(self.ctx)
        self._ConnectionMode = getConnectionMode(self.ctx)
        print("ContentProvider.__init__() %s" % self.ConnectionMode)
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
        if self.UserId != user['Id']:
            self._User = user
            checkIdentifiers(self.Connection, self.Session, self.UserId)
    @property
    def UserId(self):
        return None if self._User is None else self._User['Id']
    @property
    def UserName(self):
        return None if self._User is None else self._User['UserName']
    @property
    def ConnectionMode(self):
        return self._ConnectionMode
    @ConnectionMode.setter
    def ConnectionMode(self, mode):
        if mode == getConnectionMode(self.ctx):
            self._ConnectionMode = mode
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
            if mergeContent(self.ctx, self.Connection, event, self.ConnectionMode):
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
        print("ContentProvider.createContentIdentifier() %s" % identifier)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifier: %s ..." % identifier
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        uri = getUri(self.ctx, identifier)
        if self._hasUserName(uri) and uri.hasFragment():
            msg = "New Identifier: %s ..." % identifier
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
            fragment = uri.getFragment()
            uri.clearFragment()
            baseuri = uri.getUriReference()
            id = getIdentifier(self.Connection)
            print("ContentProvider.createContentIdentifier() createNewId %s" % id)
            newidentifier = '%s%s/%s' % (baseuri, id, fragment) if baseuri.endswith('/') else '%s/%s/%s' % (baseuri, id, fragment)
            uri = getUri(self.ctx, newidentifier)
            print("ContentProvider.createContentIdentifier() isIdentifier ******* %s" % (newidentifier, ))
        contentidentifier = ContentIdentifier(self.ctx, self.ConnectionMode, uri, self.User)
        msg = "Identifier: %s ... Done" % contentidentifier.getContentIdentifier()
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        return contentidentifier

    # XContentProvider
    def queryContent(self, identifier):
        print("ContentProvider.queryContent() %s" % identifier.getContentIdentifier())
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifier: %s..." % identifier.getContentIdentifier()
        if not identifier.IsValidUser:
            print("ContentProvider.queryContent() ERROR") 
            x = IllegalIdentifierException('Identifier need a UserName: %s' % identifier.getContentIdentifier(), self)
            e = ContentCreationException()
            e.eError = uno.Enum('com.sun.star.ucb.ContentCreationError', 'CONTENT_CREATION_FAILED')
            e.Message = 'Identifier need a UserName: %s' % identifier.getContentIdentifier()
            e.Context = self
            print("ContentProvider.queryContent() %s" % e)
            raise e
            #raise IllegalIdentifierException('Identifier need a UserName: %s' % identifier.getContentIdentifier(), None)
        if not isIdentifier(self.Connection, identifier.Id):
            raise IllegalIdentifierException('Identifier has illegal Path: %s' % identifier.getContentIdentifier(), self)
        content = self._getContent(identifier)
        if content is None:
            raise IllegalIdentifierException('Identifier has not been retrieved: %s' % identifier.getContentIdentifier(), self)
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
        elif self.UserName is None:
            username = self._getUserFromHandler()
        else:
            return True
        return self._setUser(username) if username else False

    def _getUserFromHandler(self):
        self._UserName = ''
        message = "Authentication is needed!!!"
        window = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop').ActiveFrame.ComponentWindow
        args = (getPropertyValue('Parent', window), getPropertyValue('Context', message))
        interaction = self.ctx.ServiceManager.createInstanceWithArguments('com.sun.star.task.InteractionHandler', args)
        retrieved = interaction.handleInteractionRequest(InteractionRequest(self, self.Connection, message))
        return self._UserName

    def _setUser(self, username):
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "UserName have been changed ..."
        self.Logger.logp(level, "ContentProvider", "_setUser()", msg)
        msg = "UserName retrieved from database ... "
        user = selectUser(self.Connection, username, self.ConnectionMode)
        if user is None and self.ConnectionMode == ONLINE:
            msg = "UserName retrieved from provider ... "
            user = self._getUser(username)
        if user is not None:
            self.User = user
            msg += "Done"
            self.Logger.logp(level, "ContentProvider", "_setUser()", msg)
            return True
        self._User = None
        msg = "Error: Cannot retrieve User... "
        if self.ConnectionMode == OFFLINE:
            msg += "Network is down... "
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            self.Logger.logp(level, "ContentProvider", "_setUser()", msg)
            error = InteractiveNetworkOffLineException()
            error.Message = 'NetWork is Offline...'
            error.Context = self
            error.Classification = uno.Enum('com.sun.star.task.InteractionClassification', 'QUERY')
            raise error
        return False

    def _getUser(self, username):
        user = None
        with getSession(self.ctx, username) as session:
            data, root = getUser(session)
            print("ContentProvider._getUserFromProvider(): %s" % username)
            if root is not None:
                user = mergeJsonUser(self.Connection, data, root, self.ConnectionMode)
                self.Session = session
            else:
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                msg = "ERROR: Can't retrieve User: %s from provider" % username
                self.Logger.logp(level, "ContentProvider", "_getUser()", msg)
        return user

    def _getItem(self, id):
        item = None
        data = getItem(self.Session, id)
        if data is not None:
            item = insertJsonItem(self.Connection, self.UserId, data)
        else:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = "ERROR: Can't retrieve Id from provider: %s" % id
            self.Logger.logp(level, "ContentProvider", "_getItem()", msg)            
        return item

    def _getCachedContent(self, identifier):
        if identifier.Id in self.cachedContent:
            content = self.cachedContent[identifier.Id]
            # Same Content can have multiple parent... and user...
            setContentProperties(content, {'Identifier': identifier})
        else:
            content = self._getContent(identifier)
        return content

    def _getContent(self, identifier):
        content = None
        item = selectItem(self.Connection, identifier.Id)
        if item is None and self.ConnectionMode == ONLINE:
            item = self._getItem(identifier.Id)
        if item is None:
            return None
        name, data = None, item['Data']
        mime = data['MimeType']
        data.update({'Identifier': identifier})
        if mime == g_folder:
            name = 'DriveFolderContent'
            data.update({'IsRoot': item['IsRoot'], 'Connection': self.Connection})
        elif mime == g_link:
            pass
        elif mime.startswith(g_doc):
            name = 'DriveDocumentContent'
        else:
            name = 'DriveOfficeContent'
        if name is not None:
            service = 'com.gmail.prrvchr.extensions.gDriveOOo.%s' % name
            content = createService(service, self.ctx, **data)
            content.addPropertiesChangeListener(('Name', 'Size', 'Trashed', 'Loaded', 'SyncMode'), self)
        return content

    # PropertySet
    def _getPropertySetInfo(self):
        properties = {}
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['Connection'] = getProperty('Connection', 'com.sun.star.sdbc.XConnection', maybevoid | readonly)
        properties['ConnectionMode'] = getProperty('ConnectionMode', 'short', bound)
        properties['UserName'] = getProperty('UserName', 'string', maybevoid | readonly)
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
