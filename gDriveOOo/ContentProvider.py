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
from gdrive import getDbConnection, selectUser, mergeUser, selectItem, insertItem
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
        self._User = None
        self._UserName = ''
        self.cachedContent = {}
        self.Logger = getLogger(self.ctx)
        self.ConnectionMode = getConnectionMode(self.ctx)
        print("ContentProvider.__init__() %s" % self.ConnectionMode)
        msg += " Done"
        desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
        desktop.addTerminateListener(self)
        self.Logger.logp(level, "ContentProvider", "__init__()", msg)

    @property
    def User(self):
        return self._User
    @User.setter
    def User(self, user):
        if self.UserId != user['Id']:
            self._User = user
            checkIdentifiers(self.Statement.getConnection(), self.Session, self.UserId)
    @property
    def UserId(self):
        return None if self._User is None else self._User['Id']
    @property
    def UserName(self):
        return None if self._User is None else self._User['UserName']

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
            if mergeContent(self.ctx, self.Statement.getConnection(), event, self.ConnectionMode):
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
        if self._hasUserName(uri) and uri.hasFragment():
            msg = "New Identifier: %s ..." % identifier
            self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
            uri.clearFragment()
            baseuri = uri.getUriReference()
            id = getIdentifier(self.Statement.getConnection())
            print("ContentProvider.createContentIdentifier() createNewId %s" % id)
            newidentifier = '%s%s' % (baseuri, id) if baseuri.endswith('/') else '%s/%s' % (baseuri, id)
            uri = getUri(self.ctx, newidentifier)
            print("ContentProvider.createContentIdentifier() isIdentifier ******* %s" % (newidentifier, ))
        contentidentifier = ContentIdentifier(self.ctx, self.ConnectionMode, uri, self.User)
        msg = "Identifier: %s ... Done" % contentidentifier.getContentIdentifier()
        self.Logger.logp(level, "ContentProvider", "createContentIdentifier()", msg)
        return contentidentifier

    # XContentProvider
    def queryContent(self, identifier):
        print("ContentProvider.queryContent() 1 %s" % identifier.getContentIdentifier())
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        msg = "Identifier: %s..." % identifier.getContentIdentifier()
        if not identifier.IsValidUser:
            print("ContentProvider.queryContent() 2 %s" % identifier.getContentIdentifier())
            raise IllegalIdentifierException('Identifier need a UserName: %s' % identifier.getContentIdentifier(), None)
        if not isIdentifier(self.Statement.getConnection(), identifier.Id):
            raise IllegalIdentifierException('Identifier has illegal Path: %s' % identifier.getContentIdentifier(), self)
        retrieved, content = self._getContent(identifier)
        if not retrieved:
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
        retrieved = interaction.handleInteractionRequest(InteractionRequest(self, self.Statement.getConnection(), message))
        return self._UserName

    def _setUser(self, username):
        try:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "UserName have been changed ..."
            self.Logger.logp(level, "ContentProvider", "_setUser()", msg)
            msg = "UserName retrieved from database ... "
            retrieved, user = selectUser(self.Statement.getConnection(), username, self.ConnectionMode)
            if not retrieved and self.ConnectionMode == ONLINE:
                msg = "UserName retrieved from provider ... "
                retrieved, user = self._getUser(username)
            if retrieved:
                self.User = user
                msg += "Done"
                self.Logger.logp(level, "ContentProvider", "_setUser()", msg)
            elif self.ConnectionMode == OFFLINE:
                self._User = None
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                msg = "Error: Cannot retrieve User from provider... Network is down..."
                self.Logger.logp(level, "ContentProvider", "_setUser()", msg)
            else:
                self._User = None
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                msg = "Error: Cannot retrieve User... "
                self.Logger.logp(level, "ContentProvider", "_setUser()", msg)
            return retrieved
        except Exception as e:
            print("ContentProvider._setUser().Error: %s - %s" % (e, traceback.print_exc()))

    def _getUser(self, username):
        try:
            retrieved, user, session = False, {}, getSession(self.ctx, self.Scheme, username)
            status1, usr = getUser(session)
            status2, root = getItem(session, 'root')
            print("ContentProvider._getUserFromProvider(): %s" % username)
            if status1 == codes.ok and status2 == codes.ok:
                retrieved, user = mergeUser(self.Statement.getConnection(), usr, root, self.ConnectionMode)
                self.Session = session
            else:
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                msg = "ERROR: Can't retrieve User: %s from provider" % username
                self.Logger.logp(level, "ContentProvider", "_getUser()", msg)
            return retrieved, user
        except Exception as e:
            print("ContentProvider._getUser().Error: %s - %s" % (e, traceback.print_exc()))

    def _getItem(self, id):
        retrieved, item = False, {}
        msg = None
        status, json = getItem(self.Session, id)
        if status == codes.ok:
            retrieved, item = insertItem(self.Statement.getConnection(), self.UserId, json)
        elif status == codes.bad_request:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "ERROR: Can't retrieve Id from provider: %s" % id
        else:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = "ERROR: Can't retrieve Id from provider: %s" % id
        if msg is not None:
            self.Logger.logp(level, "ContentProvider", "_getItem()", msg)            
        return retrieved, item

    def _getContent(self, identifier):
        retrieved = identifier.Id in self.cachedContent
        if retrieved:
            content = self.cachedContent[identifier.Id]
            # Same Content can have multiple parent... and user...
            setContentProperties(content, {'Identifier': identifier})
        else:
            retrieved, content = self._createContent(identifier)
        return retrieved, content

    def _createContent(self, identifier):
        id, content = identifier.Id, None
        retrieved, item = selectItem(self.Statement.getConnection(), id)
        if not retrieved and self.ConnectionMode == ONLINE:
            retrieved, item = self._getItem(id)
        if retrieved:
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
                content.addPropertiesChangeListener(('SyncMode', 'Name', 'Size'), self)
                self.cachedContent[id] = content
        return retrieved, content

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
