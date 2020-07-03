#!
# -*- coding: utf_8 -*-
import traceback

try:
    import uno
    import unohelper

    from com.sun.star.logging.LogLevel import INFO
    from com.sun.star.logging.LogLevel import SEVERE

    from com.sun.star.ucb import XContentIdentifierFactory
    from com.sun.star.ucb import XContentProvider
    from com.sun.star.ucb import XParameterizedContentProvider
    from com.sun.star.ucb import IllegalIdentifierException

    from com.sun.star.ucb import XRestContentProvider

    from unolib import getUserNameFromHandler

    from .contenttools import getUrl
    from .contenttools import getUri

    from .datasource import DataSource
    from .user import User
    from .identifier import Identifier
    from .logger import logMessage
    from .logger import getMessage

except Exception as e:
    print("clouducp.__init__() ERROR: %s - %s" % (e, traceback.print_exc()))

from threading import Event

class ContentProvider(unohelper.Base,
                      XContentIdentifierFactory,
                      XContentProvider,
                      XParameterizedContentProvider,
                      XRestContentProvider):
    def __init__(self, ctx, plugin):
        self.ctx = ctx
        self.Scheme = ''
        self.Plugin = plugin
        self.DataSource = None
        self.event = Event()
        self._defaultUser = None
        msg = "ContentProvider: %s loading ... Done" % self.Plugin
        logMessage(self.ctx, INFO, msg, 'ContentProvider', '__init__()')

    def __del__(self):
       msg = "ContentProvider: %s unloading ... Done" % self.Plugin
       logMessage(self.ctx, INFO, msg, 'ContentProvider', '__del__()')

    # XParameterizedContentProvider
    def registerInstance(self, scheme, plugin, replace):
        msg = "ContentProvider registerInstance: Scheme/Plugin: %s/%s ... Started" % (scheme, plugin)
        print(msg)
        logMessage(self.ctx, INFO, msg, 'ContentProvider', 'registerInstance()')
        try:
            print("ContentProvider.registerInstance() 1")
            datasource = DataSource(self.ctx, self.event, scheme, plugin)
            print("ContentProvider.registerInstance() 2")
        except Exception as e:
            msg = "ContentProvider registerInstance: Error: %s - %s" % (e, traceback.print_exc())
            logMessage(self.ctx, SEVERE, msg, 'ContentProvider', 'registerInstance()')
            print("ContentProvider.registerInstance() 3")
            return None
        if not datasource.IsValid:
            logMessage(self.ctx, SEVERE, datasource.Error, 'ContentProvider', 'registerInstance()')
            print("ContentProvider.registerInstance() 4")
            return None
        self.Scheme = scheme
        self.Plugin = plugin
        msg = "ContentProvider registerInstance: addCloseListener ... Done"
        logMessage(self.ctx, INFO, msg, 'ContentProvider', 'registerInstance()')
        #datasource.Connection.Parent.DatabaseDocument.addCloseListener(self)
        self.DataSource = datasource
        print("ContentProvider.registerInstance() 5")
        msg = "ContentProvider registerInstance: Scheme/Plugin: %s/%s ... Done" % (scheme, plugin)
        print(msg)
        logMessage(self.ctx, INFO, msg, 'ContentProvider', 'registerInstance()')
        return self
    def deregisterInstance(self, scheme, argument):
        msg = "ContentProvider deregisterInstance: Scheme: %s ... Done" % scheme
        logMessage(self.ctx, INFO, msg, 'ContentProvider', 'deregisterInstance()')

    # XContentIdentifierFactory
    def createContentIdentifier(self, url):
        try:
            print("ContentProvider.createContentIdentifier() 1 %s" % url)
            msg = "Identifier: %s ... " % url
            uri = getUri(self.ctx, getUrl(self.ctx, url))
            user = self._getUser(uri, url)
            identifier = Identifier(self.ctx, user, uri)
            msg += "Done"
            logMessage(self.ctx, INFO, msg, 'ContentProvider', 'createContentIdentifier()')
            print("ContentProvider.createContentIdentifier() 2")
            return identifier
        except Exception as e:
            msg += "Error: %s - %s" % (e, traceback.print_exc())
            logMessage(self.ctx, SEVERE, msg, 'ContentProvider', 'createContentIdentifier()')

    # XContentProvider
    def queryContent(self, identifier):
        url = identifier.getContentIdentifier()
        print("ContentProvider.queryContent() 1 %s" % url)
        content = identifier.getContent()
        self._defaultUser = identifier.User.Name
        msg = "Identitifer: %s ... Done" % url
        logMessage(self.ctx, INFO, msg, 'ContentProvider', 'queryContent()')
        print("ContentProvider.queryContent() 2")
        return content

    def compareContentIds(self, id1, id2):
        print("ContentProvider.compareContentIds() 1 %s - %s" % (id1, id2))
        msg = "Identifiers: %s - %s ..." % (id1, id2)
        if id1.Id == id2.Id and id1.User.Id == id2.User.Id:
            msg += " seem to be the same..."
            compare = 0
        else:
            msg += " doesn't seem to be the same..."
            compare = -1
        msg += " ... Done"
        logMessage(self.ctx, INFO, msg, 'ContentProvider', 'compareContentIds()')
        print("ContentProvider.compareContentIds() 2 %s - %s" % compare)
        return compare

    def _getUser(self, uri, url):
        if uri is None:
            error = getMessage(self.ctx, 1201, url)
            print("ContentProvider._getUser() 1 ERROR: %s" % error)
            return User(self.ctx, self.DataSource, '', error)
        if not uri.hasAuthority() or not uri.getPathSegmentCount():
            error = getMessage(self.ctx, 1202, url)
            print("ContentProvider._getUser() 2 ERROR: %s" % error)
            return User(self.ctx, self.DataSource, '', error)
        username = self._getUserName(uri, url)
        if not username:
            error = getMessage(self.ctx, 1203, url)
            print("ContentProvider._getUser() 3 ERROR: %s" % error)
            return User(self.ctx, self.DataSource, '', error)
        user = self.DataSource.getUser(username)
        if user is None:
            return User(self.ctx, self.DataSource, '', self.DataSource.Error)
        return user

    def _getUserName(self, uri, url):
        if uri.hasAuthority() and uri.getAuthority() != '':
            username = uri.getAuthority()
            print("ContentProvider._getUserName(): uri.getAuthority() = %s" % username)
        elif self._defaultUser is not None:
            username = self._defaultUser
        else:
            message = "Authentication"
            name = self.DataSource.Provider.Name
            username = getUserNameFromHandler(self.ctx, url, self, name)
            print("ContentProvider._getUserName(): getUserNameFromHandler() = %s" % username)
        print("ContentProvider._getUserName(): %s" % username)
        return username


