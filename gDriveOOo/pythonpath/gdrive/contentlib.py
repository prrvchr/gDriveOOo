#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import NoSupportException
from com.sun.star.ucb import XContentIdentifier, XContentAccess, XDynamicResultSet
from com.sun.star.ucb import XCommandInfo, XCommandInfoChangeNotifier, XContentIdentifierFactory
from com.sun.star.ucb import UnsupportedCommandException
from com.sun.star.task import XInteractionContinuation, XInteractionAbort
from com.sun.star.ucb import XInteractionSupplyName, XInteractionReplaceExistingData
from com.sun.star.ucb import IllegalIdentifierException, XInteractionSupplyAuthentication2
from com.sun.star.sdbc import XRow, XResultSet, XResultSetMetaDataSupplier
from com.sun.star.sdb import XInteractionSupplyParameters
from com.sun.star.container import XIndexAccess, XChild
from com.sun.star.task import XInteractionRequest
from com.sun.star.io import XStreamListener, XInputStreamProvider
from com.sun.star.util import XUpdatable, XLinkUpdate
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
#from com.sun.star.document import XCmisDocument

from .unolib import PropertySet
from .unotools import getProperty
from .contenttools import getUcb, getUri, getNameClashResolveRequest, getAuthenticationRequest
from .contenttools import getParametersRequest, getSession, doSync
from .identifiers import isIdentifier, getNewIdentifier, isIdentifier
from .children import updateChildren, selectChildId
from .google import InputStream

from requests.compat import unquote_plus
import traceback


class ContentUser(unohelper.Base, PropertySet):
    def __init__(self, ctx, scheme=None, user=None):
        self.user = {} if user is None else user
        self.Session = getSession(ctx, scheme, self.Name) if self.IsValid else None

    @property
    def Id(self):
        return self.user.get('Id', None)
    @property
    def Name(self):
        return self.user.get('UserName', None)
    @property
    def RootId(self):
        return self.user.get('RootId', None)
    @property
    def IsValid(self):
        return all((self.Id, self.Name, self.RootId, self.Error is None))
    @property
    def Error(self):
        return self.user.get('Error', None)

    def _getPropertySetInfo(self):
        properties = {}
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['Id'] = getProperty('Id', 'string', maybevoid | bound | readonly)
        properties['Name'] = getProperty('Name', 'string', maybevoid | bound | readonly)
        properties['RootId'] = getProperty('RootId', 'string', maybevoid | bound | readonly)
        properties['IsValid'] = getProperty('IsValid', 'boolean', bound | readonly)
        properties['Error'] = getProperty('Error', 'com.sun.star.ucb.IllegalIdentifierException', maybevoid | bound | readonly)    
        return properties


class ContentIdentifier(unohelper.Base, PropertySet, XContentIdentifier, XChild, XInputStreamProvider,
                        XUpdatable, XLinkUpdate, XContentIdentifierFactory):
    def __init__(self, ctx, connection, mode, user, uri):
        self.ctx = ctx
        self.Connection = connection
        self.Mode = mode
        self.User = user
        self.Uri = uri
        self.IsNew = self.Uri.hasFragment()
        self._Error = None
        self.size = 0
        self._Updated = False
        self.Id, self.Title, self.Url = self._parseUri() if self.User.IsValid else (None, None, None)

    @property
    def IsRoot(self):
        return self.Id == self.User.RootId
    @property
    def IsValid(self):
        return self.Id is not None
    @property
    def BaseURL(self):
        return self.Url if self.IsRoot else '%s/%s' % (self.Url, self.Id)
    @property
    def Updated(self):
        return self._Updated
    @property
    def InputStream(self):
        return self.size
    @InputStream.setter
    def InputStream(self, size):
        self.size = size
    @property
    def Error(self):
        return self._Error if self.User.Error is None else self.User.Error

    # XInputStreamProvider
    def createInputStream(self):
        return InputStream(self.User.Session, self.Id, self.size)

    # XUpdatable
    def update(self):
        self._Updated = True
        if self.Mode == ONLINE:
            with self.User.Session as session:
                self._Updated = doSync(self.ctx, self.Connection, session, self.User.Id)

    # XLinkUpdate
    def updateLinks(self):
        self._Updated = False
        if self.Mode == ONLINE:
            with self.User.Session as session:
                self._Updated = updateChildren(session, self.Connection, self.User.Id, self.Id)

    # XContentIdentifierFactory
    def createContentIdentifier(self, title=''):
        id = getNewIdentifier(self.Connection, self.User.Id)
        identifier = '%s/%s#%s' % (self.BaseURL, title, id) if title else '%s/%s' % (self.BaseURL, id)
        uri = getUri(self.ctx, identifier)
        return ContentIdentifier(self.ctx, self.Connection, self.Mode, self.User, uri)

    # XContentIdentifier
    def getContentIdentifier(self):
        return self.Uri.getUriReference()
    def getContentProviderScheme(self):
        return self.Uri.getScheme()

    # XChild
    def getParent(self):
        #print("contentlib.getParent(): ************************")
        uri = getUri(self.ctx, self.Url)
        #print("ContentIdentifier.getParent():\n    Uri: %s\n    Parent: %s" % (self.Uri.getUriReference(), uri.getUriReference()))
        return ContentIdentifier(self.ctx, self.Connection, self.Mode, self.User, uri)
    def setParent(self, parent):
        raise NoSupportException('Parent can not be set', self)

    def _parseUri(self):
        title, position, url = None, -1, None
        parentid, paths = self.User.RootId, []
        for i in range(self.Uri.getPathSegmentCount() -1, -1, -1):
            path = self.Uri.getPathSegment(i).strip()
            if path not in ('','.'):
                if title is None:
                    title = self._unquote(path)
                    position = i
                else:
                    parentid = path
                    break
        if title is None:
            id = self.User.RootId
        elif self.IsNew:
            id = self.Uri.getFragment()
        elif isIdentifier(self.Connection, title):
            id = title
        else:
            id = selectChildId(self.Connection, parentid, title)
        for i in range(position):
            paths.append(self.Uri.getPathSegment(i).strip())
        if id is None:
            id = self._searchId(paths[::-1], title)
        if id is None:
            message = "ERROR: Can't retrieve Uri: %s" % self.Uri.getUriReference()
            print("contentlib.ContentIdentifier._parseUri() Error: %s" % message)
            self._Error = IllegalIdentifierException(message, self)
        paths.insert(0, self.Uri.getAuthority())
        url = '%s://%s' % (self.Uri.getScheme(), '/'.join(paths))
        #print("ContentIdentifier._parseUri():\n    Uri: %s\n    Id - Title - Position: %s - %s - %s\n    BaseURL: %s" % (self.Uri.getUriReference(), id, title, position, url))
        return id, title, url

    def _searchId(self, paths, title):
        # Needed for be able to create a folder in a just created folder...
        paths.append(self.User.RootId)
        for index, path in enumerate(paths):
            if isIdentifier(self.Connection, path):
                id = path
                break
        for i in range(index -1, -1, -1):
            path = self._unquote(paths[i])
            id = selectChildId(self.Connection, id, path)
        id = selectChildId(self.Connection, id, title)
        return id

    def _unquote(self, text):
        # Needed for OpenOffice / LibreOffice compatibility
        if isinstance(text, str):
            text = unquote_plus(text)
        else:
            text = unquote_plus(text.encode('utf-8')).decode('utf-8')
        return text

    def _getPropertySetInfo(self):
        properties = {}
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['Connection'] = getProperty('Connection', 'com.sun.star.sdbc.XConnection', maybevoid | readonly)
        properties['Mode'] = getProperty('Mode', 'short', bound | readonly)
        properties['User'] = getProperty('User', 'com.sun.star.uno.XInterface', maybevoid | bound | readonly)
        properties['Uri'] = getProperty('Uri', 'com.sun.star.uri.XUriReference', bound | readonly)
        properties['Id'] = getProperty('Id', 'string', maybevoid | bound | readonly)
        properties['IsRoot'] = getProperty('IsRoot', 'boolean', bound | readonly)
        properties['IsValid'] = getProperty('IsValid', 'boolean', bound | readonly)
        properties['IsNew'] = getProperty('IsNew', 'boolean', bound | readonly)
        properties['BaseURL'] = getProperty('BaseURL', 'string', bound | readonly)
        properties['Title'] = getProperty('Title', 'string', maybevoid | bound | readonly)
        properties['Updated'] = getProperty('Updated', 'boolean', bound | readonly)
        properties['InputStream'] = getProperty('InputStream', 'long', maybevoid)
        properties['Error'] = getProperty('Error', 'com.sun.star.ucb.IllegalIdentifierException', maybevoid | bound | readonly)
        return properties


class InteractionRequest(unohelper.Base, XInteractionRequest):
    def __init__(self, request, continuations, result={}):
        print("InteractionRequest.__init__(): %s %s" % (request, continuations))
        self._request = request
        self._continuations = continuations

    def getRequest(self):
        return self._request
    def getContinuations(self):
        return self._continuations

class InteractionRequestAuthentication(unohelper.Base, XInteractionRequest):
    def __init__(self, source, uri, message, result):
        print("InteractionRequestAuthentication.__init__(): %s %s %s" % (source, uri, message))
        self._request = getAuthenticationRequest(source, uri, message)
        self._continuations = (InteractionSupplyAuthentication(result), InteractionAbort(result))

    def getRequest(self):
        return self._request
    def getContinuations(self):
        return self._continuations


class InteractionSupplyAuthentication(unohelper.Base, XInteractionSupplyAuthentication2):
    def __init__(self, result):
        self.result = result
        self.username = ''

    # XInteractionSupplyAuthentication2
    def canSetRealm(self):
        return False
    def setRealm(self, realm):
        pass
    def canSetUserName(self):
        return True
    def setUserName(self, username):
        self.username = username
    def canSetPassword(self):
        return False
    def setPassword(self, password):
        pass
    def getRememberPasswordModes(self, remember):
        no = uno.Enum('com.sun.star.ucb.RememberAuthentication', 'NO')
        return (), remember
    def setRememberPassword(self, remember):
        pass
    def canSetAccount(self):
        return False
    def setAccount(self, account):
        pass
    def getRememberAccountModes(self, remember):
        no = uno.Enum('com.sun.star.ucb.RememberAuthentication', 'NO')
        return (), remember
    def setRememberAccount(self, remember):
        pass
    def canUseSystemCredentials(self, default):
        return False, False
    def setUseSystemCredentials(self, default):
        pass
    def select(self):
        print("InteractionSupplyAuthentication.select()")
        self.result.update({'Retrieved': True, 'UserName': self.username})


class InteractionRequestName(unohelper.Base, XInteractionRequest):
    def __init__(self, source, message, url, name, newname, result):
        print("InteractionRequestName.__init__(): %s %s %s %s %s" % (source, message, url, name, newname))
        self._request = getNameClashResolveRequest(source, message, url, name, newname)
        self._continuations = (InteractionSupplyName(result), InteractionAbort(name, result))

    def getRequest(self):
        return self._request
    def getContinuations(self):
        return self._continuations

class InteractionSupplyName(unohelper.Base, XInteractionSupplyName):
    def __init__(self, result):
        self.result = result
        self.newtitle = ''

    def setName(self, name):
        print("InteractionSupplyName.setName(): %s" % name)
        self.newtitle = name
    def select(self):
        print("InteractionSupplyName.select()")
        self.result.update({'Retrieved': True, 'Title': self.newtitle})

class InteractionReplaceExistingData(unohelper.Base, XInteractionReplaceExistingData):
    def __init__(self, callback):
        self.callback = callback

    def select(self):
        print("InteractionReplaceExistingData.select()")


class InteractionAbort(unohelper.Base, XInteractionAbort):
    def __init__(self, result={}):
        self.result = result

    def select(self):
        self.result.update({'Retrieved': False})


class InteractionSupplyParameters(unohelper.Base, XInteractionSupplyParameters):
    def __init__(self, result):
        self.result = result
        self.username = ''

    def setParameters(self, properties):
        for property in properties:
            if property.Name == 'UserName':
                self.username = property.Value
    def select(self):
        self.result.update({'Retrieved': True, 'UserName': self.username})


class InteractionRequestParameters(unohelper.Base, XInteractionRequest):
    def __init__(self, source, connection, message, result):
        self.request = getParametersRequest(source, connection, message)
        self.request.Parameters = RequestParameters(message)
        self.continuations = (InteractionSupplyParameters(result), InteractionAbort(result))

    def getRequest(self):
        return self.request
    def getContinuations(self):
        return self.continuations


class RequestParameters(unohelper.Base, XIndexAccess):
    def __init__(self, description):
        self.description = description

    # XIndexAccess
    def getCount(self):
        return 1
    def getByIndex(self, index):
        return Parameters(self.description)
    def getElementType(self):
        return uno.getTypeByName('string')
    def hasElements(self):
        return True


class Parameters(unohelper.Base, PropertySet):
    def __init__(self, description):
        self.Name = 'UserName'
        self.Type = uno.getConstantByName('com.sun.star.sdbc.DataType.VARCHAR')
        self.TypeName = 'VARCHAR'
        self.Precision = 0
        self.Scale = 0
        self.IsNullable = uno.getConstantByName('com.sun.star.sdbc.ColumnValue.NO_NULLS')
        self.IsAutoIncrement = False
        self.IsCurrency = False
        self.IsRowVersion = False
        self.Description = description
        self.DefaultValue = ''
        
    def _getPropertySetInfo(self):
        properties = {}
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['Name'] = getProperty('Name', 'string', bound | readonly)
        properties['Type'] = getProperty('Type', 'long', bound | readonly)
        properties['TypeName'] = getProperty('TypeName', 'string', bound | readonly)
        properties['Precision'] = getProperty('Precision', 'long', bound | readonly)        
        properties['Scale'] = getProperty('Scale', 'long', bound | readonly)
        properties['IsNullable'] = getProperty('IsNullable', 'long', bound | readonly)
        properties['IsAutoIncrement'] = getProperty('IsAutoIncrement', 'boolean', bound | readonly)
        properties['IsCurrency'] = getProperty('IsCurrency', 'boolean', bound | readonly)
        properties['IsRowVersion'] = getProperty('IsRowVersion', 'boolean', bound | readonly)
        properties['Description'] = getProperty('Description', 'string', bound | readonly)
        properties['DefaultValue'] = getProperty('DefaultValue', 'string', bound | readonly)
        return properties

class CommandInfo(unohelper.Base, XCommandInfo):
    def __init__(self, commands={}):
        self.commands = commands

    # XCommandInfo
    def getCommands(self):
        print("PyCommandInfo.getCommands()")
        return tuple(self.commands.values())
    def getCommandInfoByName(self, name):
        print("PyCommandInfo.getCommandInfoByName(): %s" % name)
        if name in self.commands:
            return self.commands[name]
        print("PyCommandInfo.getCommandInfoByName() Error: %s" % name)
        msg = 'Cant getCommandInfoByName, UnsupportedCommandException: %s' % name
        raise UnsupportedCommandException(msg, self)
    def getCommandInfoByHandle(self, handle):
        print("PyCommandInfo.getCommandInfoByHandle(): %s" % handle)
        for command in self.commands.values():
            if command.Handle == handle:
                return command
        print("PyCommandInfo.getCommandInfoByHandle() Error: %s" % handle)
        msg = 'Cant getCommandInfoByHandle, UnsupportedCommandException: %s' % handle
        raise UnsupportedCommandException(msg, self)
    def hasCommandByName(self, name):
        print("PyCommandInfo.hasCommandByName(): %s" % name)
        return name in self.commands
    def hasCommandByHandle(self, handle):
        print("PyCommandInfo.hasCommandByHandle(): %s" % handle)
        for command in self.commands.values():
            if command.Handle == handle:
                return True
        return False


class CommandInfoChangeNotifier(XCommandInfoChangeNotifier):
    def __init__(self):
        self.commandInfoListeners = []

    # XCommandInfoChangeNotifier
    def addCommandInfoChangeListener(self, listener):
        self.commandInfoListeners.append(listener)
    def removeCommandInfoChangeListener(self, listener):
        if listener in self.commandInfoListeners:
            self.commandInfoListeners.remove(listener)


class Row(unohelper.Base, XRow):
    def __init__(self, namedvalues):
        self.namedvalues = namedvalues
        self.isNull = False

    # XRow
    def wasNull(self):
        return self.isNull
    def getString(self, index):
        return self._getValue(index -1)
    def getBoolean(self, index):
        return self._getValue(index -1)
    def getByte(self, index):
        return self._getValue(index -1)
    def getShort(self, index):
        return self._getValue(index -1)
    def getInt(self, index):
        return self._getValue(index -1)
    def getLong(self, index):
        return self._getValue(index -1)
    def getFloat(self, index):
        return self._getValue(index -1)
    def getDouble(self, index):
        return self._getValue(index -1)
    def getBytes(self, index):
        return self._getValue(index -1)
    def getDate(self, index):
        return self._getValue(index -1)
    def getTime(self, index):
        return self._getValue(index -1)
    def getTimestamp(self, index):
        return self._getValue(index -1)
    def getBinaryStream(self, index):
        return self._getValue(index -1)
    def getCharacterStream(self, index):
        return self._getValue(index -1)
    def getObject(self, index, map):
        return self._getValue(index -1)
    def getRef(self, index):
        return self._getValue(index -1)
    def getBlob(self, index):
        return self._getValue(index -1)
    def getClob(self, index):
        return self._getValue(index -1)
    def getArray(self, index):
        return self._getValue(index -1)

    def _getValue(self, index):
        value  = None
        self.isNull = True
        if index in range(len(self.namedvalues)):
            value = self.namedvalues[index].Value
            self.isNull = value is None
        return value
        

class DynamicResultSet(unohelper.Base, XDynamicResultSet):
    def __init__(self, ctx, identifier, select, index):
        self.ctx = ctx
        self.identifier = identifier
        self.select = select
        self.index = index

    # XDynamicResultSet
    def getStaticResultSet(self):
        return ContentResultSet(self.ctx, self.identifier, self.select, self.index)
    def setListener(self, listener):
        print("DynamicResultSet.setListener():")
        pass
    def connectToCache(self, cache):
        print("DynamicResultSet.connectToCache():")
        pass
    def getCapabilities(self):
        print("DynamicResultSet.getCapabilities():")
        return uno.getConstantByName('com.sun.star.ucb.ContentResultSetCapability.SORTED')


class ContentResultSet(unohelper.Base, PropertySet, XResultSet, XRow,
                       XResultSetMetaDataSupplier, XContentAccess):
    def __init__(self, ctx, identifier, select, index):
        self.ctx = ctx
        self.identifier = identifier
        self.resultset = select.executeQuery()
        self.RowCount = select.getLong(index)
        self.IsRowCountFinal = not select.MoreResults
        print("ContentResultSet.__init__(): %s" % self.RowCount)

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['RowCount'] = getProperty('RowCount', 'long', readonly)
        properties['IsRowCountFinal'] = getProperty('IsRowCountFinal', 'boolean', readonly)
        return properties

    # XResultSet
    def next(self):
        return self.resultset.next()
    def isBeforeFirst(self):
        return self.resultset.isBeforeFirst()
    def isAfterLast(self):
        return self.resultset.isAfterLast()
    def isFirst(self):
        return self.resultset.isFirst()
    def isLast(self):
        return self.resultset.isLast()
    def beforeFirst(self):
        self.resultset.beforeFirst()
    def afterLast(self):
        self.resultset.afterLast()
    def first(self):
        return self.resultset.first()
    def last(self):
        return self.resultset.last()
    def getRow(self):
        return self.resultset.getRow()
    def absolute(self, row):
        return self.resultset.absolute(row)
    def relative(self, row):
        return self.resultset.relative(row)
    def previous(self):
        return self.resultset.previous()
    def refreshRow(self):
        self.resultset.refreshRow()
    def rowUpdated(self):
        return self.resultset.rowUpdated()
    def rowInserted(self):
        return self.resultset.rowInserted()
    def rowDeleted(self):
        return self.resultset.rowDeleted()
    def getStatement(self):
        return self.resultset.getStatement()

    # XRow
    def wasNull(self):
        return self.resultset.wasNull()
    def getString(self, index):
        result = self.resultset.getString(index)
        #print("ContentResultSet.getString(): %s" % result)
        return result
    def getBoolean(self, index):
        return self.resultset.getBoolean(index)
    def getByte(self, index):
        return self.resultset.getByte(index)
    def getShort(self, index):
        return self.resultset.getShort(index)
    def getInt(self, index):
        return self.resultset.getInt(index)
    def getLong(self, index):
        return self.resultset.getLong(index)
    def getFloat(self, index):
        return self.resultset.getFloat(index)
    def getDouble(self, index):
        return self.resultset.getDouble(index)
    def getBytes(self, index):
        return self.resultset.getBytes(index)
    def getDate(self, index):
        return self.resultset.getDate(index)
    def getTime(self, index):
        return self.resultset.getTime(index)
    def getTimestamp(self, index):
        return self.resultset.getTimestamp(index)
    def getBinaryStream(self, index):
        return self.resultset.getBinaryStream(index)
    def getCharacterStream(self, index):
        return self.resultset.getCharacterStream(index)
    def getObject(self, index, map):
        result = self.resultset.getObject(index, map)
        #print("ContentResultSet.getObject(): %s" % result)
        return result
    def getRef(self, index):
        return self.resultset.getRef(index)
    def getBlob(self, index):
        return self.resultset.getBlob(index)
    def getClob(self, index):
        return self.resultset.getClob(index)
    def getArray(self, index):
        return self.resultset.getArray(index)

    # XResultSetMetaDataSupplier
    def getMetaData(self):
        return self.resultset.getMetaData()

    # XContentAccess
    def queryContentIdentifierString(self):
        identifier = self.resultset.getString(self.resultset.findColumn('TargetURL'))
        #print("ContentResultSet.queryContentIdentifierString(): %s" % identifier)
        return identifier
    def queryContentIdentifier(self):
        identifier = self.queryContentIdentifierString()
        uri = getUri(self.ctx, identifier)
        return ContentIdentifier(self.ctx, self.identifier.Connection, self.identifier.Mode, self.identifier.User, uri)
    def queryContent(self):
        identifier = self.queryContentIdentifier()
        return getUcb(self.ctx).queryContent(identifier)
