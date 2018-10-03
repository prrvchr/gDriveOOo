#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import NoSupportException
from com.sun.star.ucb import XContentIdentifier, XContentAccess, XDynamicResultSet
from com.sun.star.ucb import XCommandInfo, XCommandInfoChangeNotifier, UnsupportedCommandException
from com.sun.star.sdbc import XRow, XResultSet, XResultSetMetaDataSupplier
from com.sun.star.sdb import ParametersRequest
from com.sun.star.container import XIndexAccess, XChild
from com.sun.star.task import XInteractionRequest
from com.sun.star.io import XStreamListener
#from com.sun.star.document import XCmisDocument

from .unolib import PropertySet
from .unotools import getProperty
from .contenttools import getUcb, getId, getParentUri

import traceback


class ContentIdentifier(unohelper.Base, PropertySet, XContentIdentifier, XChild):
    def __init__(self, ctx, mode, uri, user):
        self.ctx = ctx
        self.ConnectionMode = mode
        self.Uri = uri
        self.user = user
        self.Id = self._getId() if self.IsValidUser else None
        
    @property
    def UserId(self):
        return self.user['Id'] if self.IsValidUser else None
    @property
    def UserName(self):
        return self.user['UserName'] if self.IsValidUser else None
    @property
    def RootId(self):
        return self.user['RootId'] if self.IsValidUser else None
    @property
    def IsRoot(self):
        return self.Id == self.RootId
    @property
    def IsValidUser(self):
        return self.user is not None

    def _getId(self):
        id = getId(self.Uri, self.RootId)
        if id in ('', '.'):
            self.Uri = getParentUri(self.ctx, self.Uri)
            id = getId(self.Uri, self.RootId)
        return id

    def _getPropertySetInfo(self):
        properties = {}
        maybevoid = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.MAYBEVOID')
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['ConnectionMode'] = getProperty('ConnectionMode', 'short', bound | readonly)
        properties['Uri'] = getProperty('Uri', 'com.sun.star.uri.XUriReference', bound | readonly)
        properties['IsValidUser'] = getProperty('IsValidUser', 'boolean', bound | readonly)
        properties['IsRoot'] = getProperty('IsRoot', 'boolean', bound | readonly)
        properties['Id'] = getProperty('Id', 'string', maybevoid | bound | readonly)
        properties['UserId'] = getProperty('UserId', 'string', maybevoid | bound | readonly)
        properties['UserName'] = getProperty('UserName', 'string', maybevoid | bound | readonly)
        return properties

    # XContentIdentifier
    def getContentIdentifier(self):
        return self.Uri.getUriReference()
    def getContentProviderScheme(self):
        return self.Uri.getScheme()

    # XChild
    def getParent(self):
        user = {'Id': self.UserId, 'UserName': self.UserName, 'RootId': self.RootId}
        uri = getParentUri(self.ctx, self.Uri)
        return ContentIdentifier(self.ctx, self.ConnectionMode, uri, user)
    def setParent(self, parent):
        raise NoSupportException('Parent can not be set', self)


class InteractionRequest(unohelper.Base, XInteractionRequest):
    def __init__(self, source, connection, message="Authentication is needed!!!"):
        self.request = ParametersRequest()
        self.request.Connection = connection
        self.request.Classification = uno.Enum('com.sun.star.task.InteractionClassification', 'QUERY')
        self.request.Message = message
        self.request.Context = source
        self.request.Parameters = RequestParameters(message)

    def getRequest(self):
        return self.request
    def getContinuations(self):
        return (self.request.Context, )


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
    def __init__(self, ctx, scheme, select, index):
        self.ctx = ctx
        self.scheme = scheme
        self.select = select
        self.index = index

    # XDynamicResultSet
    def getStaticResultSet(self):
        return ContentResultSet(self.ctx, self.scheme, self.select, self.index)
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
    def __init__(self, ctx, scheme, select, index):
        self.ctx = ctx
        self.scheme = scheme
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
        return self.resultset.getString(index)
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
        return self.resultset.getObject(index, map)
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
        return self.resultset.getString(self.resultset.findColumn('TargetURL'))
    def queryContentIdentifier(self):
        identifier = self.queryContentIdentifierString()
        return ContentIdentifier(self.scheme, identifier)
    def queryContent(self):
        identifier = self.queryContentIdentifier()
        return getUcb(self.ctx).queryContent(identifier)
