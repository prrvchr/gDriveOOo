#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.container import XIndexAccess
from com.sun.star.sdb import XInteractionSupplyParameters
from com.sun.star.sdbc import XRow
from com.sun.star.sdbc import XResultSet
from com.sun.star.sdbc import XResultSetMetaDataSupplier
from com.sun.star.task import XInteractionRequest
from com.sun.star.task import XInteractionAbort
from com.sun.star.ucb import XContentAccess
from com.sun.star.ucb import XDynamicResultSet
from com.sun.star.ucb import XCommandInfo
from com.sun.star.ucb import XCommandInfoChangeNotifier
from com.sun.star.ucb import UnsupportedCommandException
from com.sun.star.ucb import XCommandEnvironment
from com.sun.star.ucb import XInteractionSupplyName
from com.sun.star.ucb import XInteractionReplaceExistingData
from com.sun.star.ucb import XInteractionSupplyAuthentication2

from .contenttools import getUcb
from .contenttools import getNameClashResolveRequest
from .contenttools import getAuthenticationRequest
from .contenttools import getParametersRequest
from .contenttools import createContent
from .unolib import PropertySet
from .unotools import getProperty


class CommandEnvironment(unohelper.Base,
                         XCommandEnvironment):
    # XCommandEnvironment
    def getInteractionHandler(self):
        return None
    def getProgressHandler(self):
        return None


class InteractionRequest(unohelper.Base,
                         XInteractionRequest):
    def __init__(self, request, continuations, result={}):
        print("InteractionRequest.__init__(): %s %s" % (request, continuations))
        self._request = request
        self._continuations = continuations
    # XInteractionRequest
    def getRequest(self):
        return self._request
    def getContinuations(self):
        return self._continuations


class InteractionRequestAuthentication(unohelper.Base,
                                       XInteractionRequest):
    def __init__(self, source, uri, message, result):
        print("InteractionRequestAuthentication.__init__(): %s %s %s" % (source, uri, message))
        self._request = getAuthenticationRequest(source, uri, message)
        self._continuations = (InteractionSupplyAuthentication(result), InteractionAbort(result))
    # XInteractionRequest
    def getRequest(self):
        return self._request
    def getContinuations(self):
        return self._continuations


class InteractionSupplyAuthentication(unohelper.Base,
                                      XInteractionSupplyAuthentication2):
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


class InteractionRequestName(unohelper.Base,
                             XInteractionRequest):
    def __init__(self, source, message, url, name, newname, result):
        print("InteractionRequestName.__init__(): %s %s %s %s %s" % (source, message, url, name, newname))
        self._request = getNameClashResolveRequest(source, message, url, name, newname)
        self._continuations = (InteractionSupplyName(result), InteractionAbort(name, result))
    # XInteractionRequest
    def getRequest(self):
        return self._request
    def getContinuations(self):
        return self._continuations


class InteractionSupplyName(unohelper.Base,
                            XInteractionSupplyName):
    def __init__(self, result):
        self.result = result
        self.newtitle = ''
    # XInteractionSupplyName
    def setName(self, name):
        print("InteractionSupplyName.setName(): %s" % name)
        self.newtitle = name
    def select(self):
        print("InteractionSupplyName.select()")
        self.result.update({'Retrieved': True, 'Title': self.newtitle})


class InteractionReplaceExistingData(unohelper.Base,
                                     XInteractionReplaceExistingData):
    def __init__(self, callback):
        self.callback = callback
    # XInteractionReplaceExistingData
    def select(self):
        print("InteractionReplaceExistingData.select()")


class InteractionAbort(unohelper.Base,
                       XInteractionAbort):
    def __init__(self, result={}):
        self.result = result
    # XInteractionAbort
    def select(self):
        self.result.update({'Retrieved': False})


class InteractionSupplyParameters(unohelper.Base,
                                  XInteractionSupplyParameters):
    def __init__(self, result):
        self.result = result
        self.username = ''
    # XInteractionSupplyParameters
    def setParameters(self, properties):
        for property in properties:
            if property.Name == 'UserName':
                self.username = property.Value
    def select(self):
        self.result.update({'Retrieved': True, 'UserName': self.username})


class InteractionRequestParameters(unohelper.Base,
                                   XInteractionRequest):
    def __init__(self, source, connection, message, result):
        self.request = getParametersRequest(source, connection, message)
        self.request.Parameters = RequestParameters(message)
        self.continuations = (InteractionSupplyParameters(result), InteractionAbort(result))
    # XInteractionRequest
    def getRequest(self):
        return self.request
    def getContinuations(self):
        return self.continuations


class RequestParameters(unohelper.Base,
                        XIndexAccess):
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


class Parameters(unohelper.Base,
                 PropertySet):
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


class CommandInfo(unohelper.Base,
                  XCommandInfo):
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


class Row(unohelper.Base,
          XRow):
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
        

class DynamicResultSet(unohelper.Base,
                       XDynamicResultSet):
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


class ContentResultSet(unohelper.Base,
                       PropertySet,
                       XResultSet,
                       XRow,
                       XResultSetMetaDataSupplier,
                       XContentAccess):
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
        return getUcb(self.ctx).createContentIdentifier(identifier)
    def queryContent(self):
        identifier = self.queryContentIdentifier()
        return getUcb(self.ctx).queryContent(identifier)
