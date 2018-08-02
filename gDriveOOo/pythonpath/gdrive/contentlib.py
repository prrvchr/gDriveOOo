#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.ucb import XContentAccess, XDynamicResultSet, XCommandEnvironment
from com.sun.star.sdbc import XRow, XResultSet, XResultSetMetaDataSupplier, XCloseable
from com.sun.star.beans import XPropertiesChangeNotifier
#from com.sun.star.document import XCmisDocument

from .unolib import Component, PropertySet
from .unotools import createService, getProperty, getResourceLocation
from .contenttools import queryContentIdentifier, queryContent

import traceback


class CommandEnvironment(unohelper.Base, XCommandEnvironment):
    def getInteractionHandler(self):
        pass
    def getProgressHandler(self):
        pass


class Row(unohelper.Base, XRow):
    def __init__(self, values):
        print("Row.__init__()")
        self.values = values
        self.isNull = False
        print("Row.__init__(): %s" % (self.values, ))

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
        value = self._getValue(index -1)
        print("Row.getObject(): %s - %s" % (self.values[index -1].Name, value))
        return value
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
        if index in range(len(self.values)):
            value = self.values[index].Value
            self.isNull = value is None
        return value
        

class DynamicResultSet(unohelper.Base, XDynamicResultSet):
    def __init__(self, ctx, scheme, username, id, arguments):
        self.ctx = ctx
        self.scheme = scheme
        self.username = username
        self.id = id
        self.columns = []
        for property in arguments.Properties:
            if hasattr(property, 'Name'):
                self.columns.append(property.Name)
        print("DynamicResultSet.__init__(): %s" % (self.columns, ))

    # XDynamicResultSet
    def getStaticResultSet(self):
        try:
            print("DynamicResultSet.getStaticResultSet():")
            #name = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentResultSet'
            #return createService(name, self.ctx, Statement=self.statement, Columns=tuple(self.columns))
            return ContentResultSet(self.ctx, self.scheme, self.username, self.id, self.columns)
        except Exception as e:
            print("DynamicResultSet.getStaticResultSet().Error: %s - %s" % (e, traceback.print_exc()))

    def setListener(self, listener):
        print("DynamicResultSet.setListener():")
        pass
    def connectToCache(self, cache):
        print("DynamicResultSet.connectToCache():")
        pass
    def getCapabilities(self):
        print("DynamicResultSet.getCapabilities():")
        return uno.getConstantByName('com.sun.star.ucb.ContentResultSetCapability.SORTED')


class ContentResultSet(unohelper.Base, Component, PropertySet, XRow, XResultSet, XResultSetMetaDataSupplier,
                       XCloseable, XContentAccess):
    def __init__(self, ctx, scheme, username, id, columns):
        try:
# LibreOffice Column: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
# OpenOffice Columns: ['Title', 'Size', 'DateModified', 'DateCreated', 'IsFolder', 'TargetURL', 'IsHidden', 'IsVolume', 'IsRemote', 'IsRemoveable', 'IsFloppy', 'IsCompactDisc']
            self.ctx = ctx
            self.scheme = scheme
            self.username = username
            url = getResourceLocation(self.ctx, '%s.odb' % scheme)
            db = createService('com.sun.star.sdb.DatabaseContext').getByName(url)
            connection = db.getConnection('', '')
            query = uno.getConstantByName('com.sun.star.sdb.CommandType.QUERY')
            statement = connection.prepareCommand('getChildren', query)
            statement.ResultSetType = uno.getConstantByName('com.sun.star.sdbc.ResultSetType.SCROLL_SENSITIVE')
            statement.ResultSetConcurrency = uno.getConstantByName('com.sun.star.sdbc.ResultSetConcurrency.UPDATABLE')
            statement.setString(1, username)
            statement.setString(2, id)
            self.resultset = statement.executeQuery()
            self.columns = columns
            self.resultset.last()
            self.RowCount = self.resultset.getRow()
            self.IsRowCountFinal = True
            self.resultset.beforeFirst()
            self.listeners = []
            print("ContentResultSet.__init__() %s" % self.RowCount)
        except Exception as e:
            print("ContentResultSet.__init__().Error: %s" % e)

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

    # XContentAccess
    def queryContentIdentifierString(self):
        identifier = self.resultset.getColumns().getByName('TargetURL').getString()
        print("ContentResultSet.queryContentIdentifierString() %s" % identifier)
        return identifier
    def queryContentIdentifier(self):
        identifier = self.queryContentIdentifierString()
        print("ContentResultSet.queryContentIdentifier() %s" % identifier)
        return queryContentIdentifier(self.ctx, identifier)
    def queryContent(self):
        identifier = self.queryContentIdentifierString()
        print("ContentResultSet.queryContent() %s" % identifier)
        return queryContent(self.ctx, identifier)

    # XResultSetMetaDataSupplier
    def getMetaData(self):
        print("ContentResultSet.getMetaData()")
        return self.resultset.getMetaData()

    # XCloseable
    def close(self):
        print("ContentResultSet.close() *****************************************************")
        pass

    # XRow
    def wasNull(self):
        wasnull = self.resultset.wasNull()
        return wasnull
    def getString(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.resultset.getColumns().getByName(column).getString()
        print("contentlib.Row().getString() %s - %s" % (column, value))
        return value
    def getBoolean(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.resultset.getColumns().getByName(column).getBoolean()
        return value
    def getByte(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getByte()
    def getShort(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.resultset.getColumns().getByName(column).getShort()
        return value
    def getInt(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.resultset.getColumns().getByName(column).getInt()
        return value
    def getLong(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.resultset.getColumns().getByName(column).getLong()
        return value
    def getFloat(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.resultset.getColumns().getByName(column).getFloat()
        return value
    def getDouble(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.resultset.getColumns().getByName(column).getDouble()
        return value
    def getBytes(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getBytes()
    def getDate(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getDate()
    def getTime(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getTime()
    def getTimestamp(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.resultset.getColumns().getByName(column).getTimestamp()
        return value
    def getBinaryStream(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getBinaryStream()
    def getCharacterStream(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getCharacterStream()
    def getObject(self, index, map):
        column = self._getColumn(index)
        value = None if column is None else self.resultset.getColumns().getByName(column).getObject(map)
        print("contentlib.Row().getObject() %s - %s" % (column, value))
        return value
    def getRef(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getRef()
    def getBlob(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getBlob()
    def getClob(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getClob()
    def getArray(self, index):
        column = self._getColumn(index)
        return None if column is None else self.resultset.getColumns().getByName(column).getArray()

    def _getColumn(self, index):
        name  = None
        column = None
        if index > 0 and index <= len(self.columns):
            name = self.columns[index -1]
            if self.resultset.getColumns().hasByName(name):
                column = name
        if column is None:
            print("Row._getColumn(): %s - %s *************************************" % (index, name))
        return column


class PropertiesChangeNotifier(XPropertiesChangeNotifier):
    def __init__(self):
        print("PyPropertiesChangeNotifier.__init__()")
        self.propertiesListener = {}

    #XPropertiesChangeNotifier
    def addPropertiesChangeListener(self, names, listener):
        print("PyPropertiesChangeNotifier.addPropertiesChangeListener()")
        for name in names:
            if name not in self.propertiesListener:
                self.propertiesListener[name] = []
            self.propertiesListener[name].append(listener)
    def removePropertiesChangeListener(self, names, listener):
        print("PyPropertiesChangeNotifier.removePropertiesChangeListener()")
        for name in names:
            if name in self.propertiesListener:
                if listener in self.propertiesListener[name]:
                    self.propertiesListener[name].remove(listener)

'''
class XCmisDocument(unohelper.Base, XCmisDocument):
    def __init__(self, cmisproperties={}):
        self._CmisProperties = cmisproperties

    @property
    def CmisProperties(self):
        return tuple(self._CmisProperties.values)

    #XCmisDocument
    def checkOut(self):
        pass
    def cancelCheckOut(self):
        pass
    def checkIn(self, ismajor, comment):
        pass
    def isVersionable(self):
        return True
    def canCheckOut(self):
        return True
    def canCancelCheckOut(self):
        return True
    def canCheckIn (self):
        return True
    def updateCmisProperties(self, cmisproperties):
        for cmisproperty in cmisproperties:
            id = cmisproperty.Id
            if id in self._CmisProperties:
                self._CmisProperties[id] = cmisproperty
    def getAllVersions(self):
        return ()
'''
