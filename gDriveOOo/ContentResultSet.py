#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo, XInitialization
from com.sun.star.beans import XPropertySet, XPropertySetInfo
from com.sun.star.sdbc import XRow, XResultSet, XResultSetMetaDataSupplier
from com.sun.star.sdbc import XCloseable
from com.sun.star.ucb import XContentAccess

import gdrive

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentResultSet'


'''
class ContentResultSet(unohelper.Base, XServiceInfo, XInitialization, XPropertySet, XRow, XResultSet,
                       XResultSetUpdate, XResultSetMetaDataSupplier, XColumnLocate, XRowUpdate,
                       XWarningsSupplier, XColumnsSupplier, XDeleteRows, XRowLocate, XCloseable,
                       XCancellable, XPropertyChangeListener, XVetoableChangeListener, XContentAccess):
'''

class ContentResultSet(unohelper.Base, XServiceInfo, XInitialization, XRow, XPropertySet, XResultSet,
                       XResultSetMetaDataSupplier, XCloseable, XContentAccess):
    def __init__(self, ctx, *namedvalues):
        try:
            print("ContentResultSet.__init__")
            self.ctx = ctx
            self.Statement = None
            self.Columns = []
            self.properties = self._getPropertySetInfo()
            self.initialize(namedvalues)
            self.ResultSet = self.Statement.executeQuery()
            self.IsRowCountFinal = True
            self.ResultSet.last()
            self.RowCount = self.ResultSet.getRow()
            self.ResultSet.beforeFirst()
            print("ContentResultSet.__init__")
        except Exception as e:
            print("ContentResultSet.__init__().Error: %s" % e)

    # XContentAccess
    def queryContentIdentifierString(self):
        print("ContentResultSet.queryContentIdentifierString()")
        scheme = self.ResultSet.getColumns().getByName('Scheme').getString()
        username = self.ResultSet.getColumns().getByName('UserName').getString()
        id = self.ResultSet.getColumns().getByName('Id').getString()
        return gdrive.queryContentIdentifierString(scheme, username, id)
    def queryContentIdentifier(self):
        scheme = self.ResultSet.getColumns().getByName('Scheme').getString()
        username = self.ResultSet.getColumns().getByName('UserName').getString()
        id = self.ResultSet.getColumns().getByName('Id').getString()
        return gdrive.queryContentIdentifier(self.ctx, scheme, username, id)
    def queryContent(self):
        scheme = self.ResultSet.getColumns().getByName('Scheme').getString()
        username = self.ResultSet.getColumns().getByName('UserName').getString()
        id = self.ResultSet.getColumns().getByName('Id').getString()
        return gdrive.queryContent(self.ctx, scheme, username, id)

    # XInitialization
    def initialize(self, namedvalues=()):
        for namedvalue in namedvalues:
            if hasattr(namedvalue, 'Name') and hasattr(namedvalue, 'Value') and hasattr(self, namedvalue.Name):
                setattr(self, namedvalue.Name, namedvalue.Value)

    # XPropertySet
    def getPropertySetInfo(self):
        print("ContentResultSet.getPropertySetInfo()")
        return PropertySetInfo(self.properties)
    def setPropertyValue(self, name, value):
        print("ContentResultSet.setPropertyValue() %s - %s" % (name, value))
        if name in self.properties and hasattr(self, name):
            setattr(self, name, value)
    def getPropertyValue(self, name):
        print("ContentResultSet.getPropertyValue() %s" % (name, ))
        if name in self.properties and hasattr(self, name):
            return getattr(self, name)
    def addPropertyChangeListener(self, name, listener):
        pass
    def removePropertyChangeListener(self, name, listener):
        pass
    def addVetoableChangeListener(self, name, listener):
        pass
    def removeVetoableChangeListener(self, name, listener):
        pass

    # XRow
    def wasNull(self):
        wasnull = self.ResultSet.wasNull()
        return wasnull
    def getString(self, index):
        value = None
        column = self._getColumn(index)
        if column is not None:
            value = self.ResultSet.getColumns().getByName(column).getString()
        print("ContentResultSet.Row().getString() %s - %s" % (column, value))
        return value
    def getBoolean(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.ResultSet.getColumns().getByName(column).getBoolean()
        return value
    def getByte(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getByte()
    def getShort(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.ResultSet.getColumns().getByName(column).getShort()
        return value
    def getInt(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.ResultSet.getColumns().getByName(column).getInt()
        return value
    def getLong(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.ResultSet.getColumns().getByName(column).getLong()
        return value
    def getFloat(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.ResultSet.getColumns().getByName(column).getFloat()
        return value
    def getDouble(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.ResultSet.getColumns().getByName(column).getDouble()
        return value
    def getBytes(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getBytes()
    def getDate(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getDate()
    def getTime(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getTime()
    def getTimestamp(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.ResultSet.getColumns().getByName(column).getTimestamp()
        return value
    def getBinaryStream(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getBinaryStream()
    def getCharacterStream(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getCharacterStream()
    def getObject(self, index, map):
        column = self._getColumn(index)
        value = None if column is None else self.ResultSet.getColumns().getByName(column).getObject(map)
        print("ContentResultSet.Row().getObject() %s - %s" % (column, value))
        return value
    def getRef(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getRef()
    def getBlob(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getBlob()
    def getClob(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getClob()
    def getArray(self, index):
        column = self._getColumn(index)
        return None if column is None else self.ResultSet.getColumns().getByName(column).getArray()

    # XResultSet
    def next(self):
        next = self.ResultSet.next()
        print("ContentResultSet.next() %s" % next)
        return next
    def isBeforeFirst(self):
        return self.ResultSet.isBeforeFirst()
    def isAfterLast(self):
        return self.ResultSet.isAfterLast()
    def isFirst(self):
        return self.ResultSet.isFirst()
    def isLast(self):
        return self.ResultSet.isLast()
    def beforeFirst(self):
        self.ResultSet.beforeFirst()
    def afterLast(self):
        self.ResultSet.afterLast()
    def first(self):
        return self.ResultSet.first()
    def last(self):
        return self.ResultSet.last()
    def getRow(self):
        return self.ResultSet.getRow()
    def absolute(self, row):
        return self.ResultSet.absolute(row)
    def relative(self, row):
        return self.ResultSet.relative(row)
    def previous(self):
        return self.ResultSet.previous()
    def refreshRow(self):
        self.ResultSet.refreshRow()
    def rowUpdated(self):
        return self.ResultSet.rowUpdated()
    def rowInserted(self):
        return self.ResultSet.rowInserted()
    def rowDeleted(self):
        return self.ResultSet.rowDeleted()
    def getStatement(self):
        return self.ResultSet.getStatement()

    # XResultSetMetaDataSupplier
    def getMetaData(self):
        print("ContentResultSet.getMetaData()")
        return self.ResultSet.getMetaData()

    # XCloseable
    def close(self):
        #self.ResultSet.close()
        print("ContentResultSet.close() *****************************************")

    # XCancellable
#    def cancel(self):
#        self.ResultSet.cancel()

    # XEventListener
    def disposing(self, source):
        print("ContentResultSet.disposing()")
        #self.ResultSet.disposing(source)'

    def _getColumn(self, index):
        name  = None
        column = None
        if index > 0 and index <= len(self.Columns):
            name = self.Columns[index -1]
            if self.ResultSet.getColumns().hasByName(name):
                column = name
        if column is None:
            print("ContentResultSet._getColumn(): %s - %s *************************************" % (index, name))
        return column

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['RowCount'] = gdrive.getProperty('RowCount', 'long', readonly)
        properties['IsRowCountFinal'] = gdrive.getProperty('IsRowCountFinal', 'boolean', readonly)
        return properties

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


class PropertySetInfo(unohelper.Base, XPropertySetInfo):
    def __init__(self, properties):
        self.properties = properties

    # XPropertySetInfo
    def getProperties(self):
        print("PropertySetInfo.getProperties()")
        return tuple(self.properties.values())
    def getPropertyByName(self, name):
        property = None
        print("PyPropertySetInfo.getPropertyByName() %s" % (name, ))
        if name in self.properties:
            property = self.properties[name]
        return property
    def hasPropertyByName(self, name):
        print("PropertySetInfo.hasPropertyByName(): %s" % (name, ))
        return name in self.properties


g_ImplementationHelper.addImplementation(ContentResultSet,                          # UNO object class
                                         g_ImplementationName,                      # Implementation name
                                        (g_ImplementationName,))                    # List of implemented services
