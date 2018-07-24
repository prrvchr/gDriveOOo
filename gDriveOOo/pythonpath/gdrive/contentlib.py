#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.ucb import XContentAccess, XDynamicResultSet, IllegalIdentifierException, XCommandInfoChangeNotifier
from com.sun.star.sdbc import XRow, XResultSet, XResultSetMetaDataSupplier, XResultSetMetaData, XCloseable
from com.sun.star.io import XStream, XInputStream, XOutputStream, XSeekable, XActiveDataSink
from com.sun.star.io import XActiveDataSource, XActiveDataControl, NotConnectedException, IOException
from com.sun.star.io import XStreamListener
from com.sun.star.beans import XPropertiesChangeNotifier, XPropertySetInfoChangeNotifier
from com.sun.star.lang import IllegalArgumentException
from com.sun.star.uno import Exception
#from com.sun.star.document import XCmisDocument

from .unolib import PyPropertySet
from . import unotools
from . import contenttools
import requests
import base64
import traceback


class Row(unohelper.Base, XRow):
    def __init__(self, statement, arguments):
        print("Row.__init__()")
        self.resultset = statement.executeQuery()
        self.resultset.next()
        self.columnset = self.resultset.getColumns()
        self.columns = []
        for property in arguments:
            if hasattr(property, 'Name'):
                #if property.Name == 'CasePreservingURL':
                #    id = createIdentifier(self.auth, self.url, self.Title)
                #    value = queryContentIdentifierString(self.Scheme, self.UserName, id)
                self.columns.append(property.Name)
        print("Row.__init__(): %s" % (self.columns, ))

    # XRow
    def wasNull(self):
        wasnull = self.resultset.wasNull()
        return wasnull
    def getString(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.columnset.getByName(column).getString()
        print("contentlib.Row().getString() %s - %s" % (column, value))
        return value
    def getBoolean(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.columnset.getByName(column).getBoolean()
        return value
    def getByte(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getByte()
    def getShort(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.columnset.getByName(column).getShort()
        return value
    def getInt(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.columnset.getByName(column).getInt()
        return value
    def getLong(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.columnset.getByName(column).getLong()
        return value
    def getFloat(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.columnset.getByName(column).getFloat()
        return value
    def getDouble(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.columnset.getByName(column).getDouble()
        return value
    def getBytes(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getBytes()
    def getDate(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getDate()
    def getTime(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getTime()
    def getTimestamp(self, index):
        column = self._getColumn(index)
        value = None if column is None else self.columnset.getByName(column).getTimestamp()
        return value
    def getBinaryStream(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getBinaryStream()
    def getCharacterStream(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getCharacterStream()
    def getObject(self, index, map):
        column = self._getColumn(index)
        value = None if column is None else self.columnset.getByName(column).getObject(map)
        print("contentlib.Row().getObject() %s - %s" % (column, value))
        return value
    def getRef(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getRef()
    def getBlob(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getBlob()
    def getClob(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getClob()
    def getArray(self, index):
        column = self._getColumn(index)
        return None if column is None else self.columnset.getByName(column).getArray()

    def _getColumn(self, index):
        name  = None
        column = None
        if index > 0 and index <= len(self.columns):
            name = self.columns[index -1]
            if self.columnset.hasByName(name):
                column = name
        if column is None:
            print("Row._getColumn(): %s - %s *************************************" % (index, name))
        return column
        

class DynamicResultSet(unohelper.Base, XDynamicResultSet):
    def __init__(self, ctx, statement, arguments):
        self.ctx = ctx
        self.statement = statement
        self.columns = []
        for property in arguments.Properties:
            if hasattr(property, 'Name'):
                self.columns.append(property.Name)
        print("DynamicResultSet.__init__(): %s" % (self.columns, ))

    # XDynamicResultSet
    def getStaticResultSet(self):
        try:
            print("DynamicResultSet.getStaticResultSet():")
            name = 'com.gmail.prrvchr.extensions.gDriveOOo.ContentResultSet'
            return unotools.createService(name, self.ctx, Statement=self.statement, Columns=tuple(self.columns))
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


class ContentResultSet(Row, PyPropertySet, XResultSet, XResultSetMetaDataSupplier,
                       XCloseable, XContentAccess):
    def __init__(self, ctx, statement, id, columns):
        try:
            self.ctx = ctx
            statement.setString(2, id)
            self.resultset = statement.executeQuery()
            self.columnset = self.resultset.getColumns()
            self.columns = columns
            self.IsRowCountFinal = True
            self.resultset.last()
            self.RowCount = self.resultset.getRow()
            self.resultset.beforeFirst()
            self.properties = self._getPropertySetInfo()
            print("ContentResultSet.__init__() %s" % self.RowCount)
        except Exception as e:
            print("ContentResultSet.__init__().Error: %s" % e)

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['RowCount'] = unotools.getProperty('RowCount', 'long', readonly)
        properties['IsRowCountFinal'] = unotools.getProperty('IsRowCountFinal', 'boolean', readonly)
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
        scheme = self.columnset.getByName('Scheme').getString()
        username = self.columnset.getByName('UserName').getString()
        id = self.columnset.getByName('FileId').getString()
        print("ContentResultSet.queryContentIdentifierString() %s" % id)
        return contenttools.queryContentIdentifierString(scheme, username, id)
    def queryContentIdentifier(self):
        scheme = self.columnset.getByName('Scheme').getString()
        username = self.columnset.getByName('UserName').getString()
        id = self.columnset.getByName('FileId').getString()
        print("ContentResultSet.queryContentIdentifier() %s" % id)
        return contenttools.queryContentIdentifier(self.ctx, scheme, username, id)
    def queryContent(self):
        scheme = self.columnset.getByName('Scheme').getString()
        username = self.columnset.getByName('UserName').getString()
        id = self.columnset.getByName('FileId').getString()
        print("ContentResultSet.queryContent() %s" % id)
        return contenttools.queryContent(self.ctx, scheme, username, id)

    # XResultSetMetaDataSupplier
    def getMetaData(self):
        print("ContentResultSet.getMetaData()")
        return self.resultset.getMetaData()

    # XCloseable
    def close(self):
        print("ContentResultSet.close()")
        pass





class PyPropertiesChangeNotifier(XPropertiesChangeNotifier):
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
                self.propertiesListener[name].remove(listener)


class PyPropertySetInfoChangeNotifier(XPropertySetInfoChangeNotifier):
    def __init__(self):
        print("PyPropertySetInfoChangeNotifier.__init__()")
        self.propertyInfoListeners = []
    #XPropertySetInfoChangeNotifier
    def addPropertySetInfoChangeListener(self, listener):
        print("PyPropertySetInfoChangeNotifier.addPropertySetInfoChangeListener()")
        self.propertyInfoListeners.append(listener)
    def removePropertySetInfoChangeListener(self, listener):
        print("PyPropertySetInfoChangeNotifier.removePropertySetInfoChangeListener()")
        if listener in self.propertyInfoListeners:
            self.propertyInfoListeners.remove(listener)


class PyCommandInfoChangeNotifier(XCommandInfoChangeNotifier):
    def __init__(self):
        print("PyCommandInfoChangeNotifier.__init__()")
        self.commandInfoListeners = []
    #XCommandInfoChangeNotifier
    def addCommandInfoChangeListener(self, listener):
        print("PyCommandInfoChangeNotifier.addCommandInfoChangeListener()")
        self.commandInfoListeners.append(listener)
    def removeCommandInfoChangeListener(self, listener):
        print("PyCommandInfoChangeNotifier.removeCommandInfoChangeListener()")
        if listener in self.commandInfoListeners:
            self.commandInfoListeners.remove(listener)


class PyRow(unohelper.Base, XRow):
    def __init__(self, values=()):
        self.values = values
        self._isNull = True

    # XRow
    def wasNull(self):
        return self._isNull
    def getString(self, index):
        return self._getValue(index)
    def getBoolean(self, index):
        return self._getValue(index)
    def getByte(self, index):
        return self._getValue(index)
    def getShort(self, index):
        return self._getValue(index)
    def getInt(self, index):
        return self._getValue(index)
    def getLong(self, index):
        return self._getValue(index)
    def getFloat(self, index):
        return self._getValue(index)
    def getDouble(self, index):
        return self._getValue(index)
    def getBytes(self, index):
        return self._getValue(index)
    def getDate(self, index):
        return self._getValue(index)
    def getTime(self, index):
        return self._getValue(index)
    def getTimestamp(self, index):
        return self._getValue(index)
    def getBinaryStream(self, index):
        return self._getValue(index)
    def getCharacterStream(self, index):
        return self._getValue(index)
    def getObject(self, index, map):
        return self._getValue(index)
    def getRef(self, index):
        return self._getValue(index)
    def getBlob(self, index):
        return self._getValue(index)
    def getClob(self, index):
        return self._getValue(index)
    def getArray(self, index):
        return self._getValue(index)

    def _getValue(self, index):
        value = None
        if index > 0 and index <= len(self.values):
            value = self.values[index -1]
        self._isNull = value is None
        return value


class PyGoogleDriveContentResultSet(PyRow, PyPropertySet, XResultSet, XResultSetMetaDataSupplier,
                                    XCloseable, XContentAccess):
    def __init__(self, ctx, username, rows, columns, final):
        try:
            self.ctx = ctx
            self.Scheme = 'vnd.google-apps'
            self.UserName = username
            self.Rows = rows
            self.Columns = columns
            self.IsRowCountFinal = final
            self.row = {}
            self._index = 0
            self._isNull = True
            self.properties = self._getPropertySetInfo()
            print("PyGoogleDriveContentResultSet.__init__()")
        except Exception as e:
            print("PyGoogleDriveContentResultSet.__init__().Error: %s" % e)

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        properties['RowCount'] = unotools.getProperty('RowCount', 'long', readonly)
        properties['IsRowCountFinal'] = unotools.getProperty('IsRowCountFinal', 'boolean', readonly)
        return properties

    @property
    def index(self):
        return self._index
    @index.setter
    def index(self, index):
        self.row = {}
        if index > 0 and index <= self.RowCount:
            self.row = self.Rows[index -1]
        self._index = index
    @property
    def RowCount(self):
        return len(self.Rows)

    # XResultSet
    def next(self):
        if not self.isLast():
            self.index += 1
            return True
        return False
    def isBeforeFirst(self):
        return self.index == 0
    def isAfterLast(self):
        return self.index == self.RowCount +1
    def isFirst(self):
        return self.index == 1
    def isLast(self):
        return self.index == self.RowCount
    def beforeFirst(self):
        self.index = 0
    def afterLast(self):
        self.index = self.RowCount +1
    def first(self):
        if self.RowCount:
            self.index = 1
            return True
        return False
    def last(self):
        if self.RowCount:
            self.index = self.RowCount
            return True
        return False
    def getRow(self):
        return self.index
    def absolute(self, row):
        if row < 0:
            index = self.RowCount + row +1
            if index >= 1:
                self.index = index
                return True
            return False
        elif row > 0:
            if row <= self.RowCount:
                self.index = row
                return True
            return False
        return True
    def relative(self, row):
        return self.index
    def previous(self):
        if not self.isFirst():
            self.index -= 1
            return True
        return False
    def refreshRow(self):
        pass
    def rowUpdated(self):
        return False
    def rowInserted(self):
        return False
    def rowDeleted(self):
        return False
    def getStatement(self):
        return None

    # XContentAccess
    def queryContentIdentifierString(self):
        id = self._getValueByName('FileId')
        return contenttools.queryContentIdentifierString(self.Scheme, self.UserName, id)
    def queryContentIdentifier(self):
        id = self._getValueByName('FileId')
        return contenttools.queryContentIdentifier(self.ctx, self.Scheme, self.UserName, id)
    def queryContent(self):
        id = self._getValueByName('FileId')
        return contenttools.queryContent(self.ctx, self.Scheme, self.UserName, id)

    # XResultSetMetaDataSupplier
    def getMetaData(self):
        print("PyGoogleDriveContentResultSet.getMetaData()")
        return PyResultSetMetaData(self.properties, self.Columns)

    # XCloseable
    def close(self):
        print("PyGoogleDriveContentResultSet.close()")
        pass

    # XRow
    def _getValue(self, index):
        value = None
        if index > 0 and index <= len(self.Columns):
            name = self.Columns[index -1]
            value = self._getValueByName(name)
        else:
            print("PyGoogleDriveContentResultSet._getValue(): %s - %s" % (name, value))
        self._isNull = value is None
        return value

    def _getValueByName(self, name):
        value = None
        if name == 'FileId':
            if 'id' in self.row:
                value = self.row['id']
        elif name == 'Title':
            if 'name' in self.row:
                value = self.row['name']
        elif name == 'ContentType':
            if 'mimeType' in self.row:
                value = self.row['mimeType']
        elif name == 'IsFolder':
            if 'mimeType' in self.row:
                value = self.row['mimeType'] == 'application/vnd.google-apps.folder'
        elif name == 'IsDocument':
            if 'mimeType' in self.row:
                value = self.row['mimeType'] != 'application/vnd.google-apps.folder'
        elif name == 'IsHidden':
            value = False
        elif name == 'IsVolume':
            value = False
        elif name == 'IsRemote':
            value = False
        elif name == 'IsRemoveable':
            value = False
        elif name == 'IsFloppy':
            value = False
        elif name == 'IsCompactDisc':
            value = False
        elif name == 'TargetURL':
            value = contenttools.queryContentIdentifierString(self.Scheme, self.UserName, self.row['id'])
        elif name == 'Size':
            value = int(self.row['size']) if 'size' in self.row else 0
        elif name == 'DateModified':
            value = contenttools.parseDateTime(self.row['modifiedTime'])
        elif name == 'ParentsId':
            value = tuple(self.row['parents']) if 'parents' in self.row else ()
        elif name == 'ContentType':
            value = self.row['mimeType'] if 'mimeType' in self.row else 'octet/stream'
        return value


class PyDynamicResultSet(unohelper.Base, XDynamicResultSet):
    def __init__(self, ctx, username, rows, columns, final):
        self.ctx = ctx
        self.username = username
        self.rows = rows
        self.columns = columns
        self.final = final
        print("PyDynamicResultSet.__init__()")

    # XDynamicResultSet
    def getStaticResultSet(self):
        print("PyDynamicResultSet.getStaticResultSet():")
        return PyGoogleDriveContentResultSet(self.ctx, self.username, self.rows, self.columns, self.final)

    def setListener(self, listener):
        print("PyDynamicResultSet.setListener():")
        pass
    def connectToCache(self, cache):
        print("PyDynamicResultSet.connectToCache():")
        pass
    def getCapabilities(self):
        print("PyDynamicResultSet.getCapabilities():")
        return uno.getConstantByName('com.sun.star.ucb.ContentResultSetCapability.SORTED')


class PyResultSetMetaData(XResultSetMetaData):
    def __init__(self, properties={}, columns=[]):
        self.properties = properties
        self.columns = columns

    # XResultSetMetaData
    def getColumnCount(self):
        return len(self.columns)
    def isAutoIncrement(self, column):
        return False
    def isCaseSensitive(self, column):
        return True
    def isSearchable(self, column):
        return False
    def isCurrency(self, column):
        return False
    def isNullable(self, column):
        return False
    def isSigned(self, column):
        return False
    def getColumnDisplaySize(self, column):
        return len(self.columns[column])
    def getColumnLabel(self, column):
        return self.columns[column]
    def getColumnName(self, column):
        return self.columns[column]
    def getSchemaName(self, column):
        return self.columns[column]
    def getPrecision(self, column):
        return 2
    def getScale(self, column):
        return 9
    def getTableName(self, column):
        return self.columns[column]
    def getCatalogName(self, column):
        return self.columns[column]
    def getColumnType(self, column):
        return column
    def getColumnTypeName(self, column):
        typename = 'string'
        name = self.columns[column]
        for property in self.properties:
            if property.Name == name:
                typename = property.Type.getType().getTypeName()
                break   
        return typename
    def isReadOnly(self, column):
        name = self.columns[column]
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        for property in self.properties:
            if property.Name == name and property.Attributes & readonly:
                return True
        return False
    def isWritable(self, column):
        return not self.isReadOnly(column)
    def isDefinitelyWritable(self, column):
        return self.isWritable(column)
    def getColumnServiceName(self, column):
        return 'str'


class PyActiveDataSink(unohelper.Base, XActiveDataSink, XActiveDataControl):
    def __init__(self, auth, location, size, mimetype, chunk):
        self.auth = auth
        self.location = location
        self.size = size
        self.mimetype = mimetype
        self.chunk = chunk
        self.listeners = []
        self.input = None
        self.canceled = False
        self.error = ''
    #XActiveDataSink
    def setInputStream(self, input):
        self.input = input
    def getInputStream(self):
        return self.input

    #XActiveDataControl
    def addListener(self, listener):
        self.listeners.append(listener)
    def removeListener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)
    def start(self):
        for listener in self.listeners:
            listener.started()
        print("contentlib.PyActiveDataSink.start() 1")
        start = 0
        session = requests.Session()
        headers = {}
        headers['Content-Range'] = 'bytes */%s' % self.size
        with session.put(self.location, headers=headers, auth=self.auth) as r:
            if r.status_code == requests.codes.ok:
                if 'Range' in r.headers:
                    start = int(r.headers['Range'].split('-')[-1]) +1
        chunk = min(self.size, self.chunk)
        headers['Content-Type'] = self.mimetype
        while start < self.size and not self.canceled:
            end = min(start + chunk -1, self.size -1)
            headers['Content-Range'] = 'bytes %s-%s/%s' % (start, end, self.size)
            print("contentlib.PyActiveDataSink.start() 2 %s" % (headers['Content-Range'], ))
            length, sequence = self.input.readBytes(None, chunk)
            data = sequence.value
            with session.put(self.location, headers=headers, data=data, auth=self.auth) as r:
                print("contentlib.PyActiveDataSink.start() 3 %s %s" % (r.status_code, r.headers))
                if r.status_code == requests.codes.ok or r.status_code == requests.codes.created:
                    start += length
                elif r.status_code == requests.codes.permanent_redirect:
                    if 'Range' in r.headers:
                        start += int(r.headers['Range'].split('-')[-1]) +1
                else:
                    self.error = 'http error status:%s - headers:%s' % (r.status_code, r.headers)
                    break
        self.input.closeInput()
        for listener in self.listeners:
            if self.error:
                listener.error(Exception(self.error, self))
            if self.canceled:
                listener.terminated()
            listener.closed()
        print("contentlib.PyActiveDataSink.start()4")
    def terminate(self):
        self.canceled = True


class PyActiveDataSource(unohelper.Base, XActiveDataSource, XActiveDataControl):
    def __init__(self, auth, id, size, chunk):
        self.url = 'https://www.googleapis.com/drive/v3/files/%s' % id
        self.auth = auth
        self.size = size
        self.chunk = chunk
        self.listeners = []
        self.output = None
        self.canceled = False
        self.error = ''
    #XActiveDataSource
    def setOutputStream(self, output):
        self.output = output
    def getOutputStream(self):
        return self.output

    #XActiveDataControl
    def addListener(self, listener):
        self.listeners.append(listener)
    def removeListener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)
    def start(self):
        for listener in self.listeners:
            listener.started()
        start = 0
        chunk = min(self.size, self.chunk)
        print("contentlib.PyActiveDataSource.start()1")
        session = requests.Session()
        headers = {}
        headers['Content-Type'] = None
        headers['Accept-Encoding'] = 'gzip'
        params = {'alt': 'media'}
        while start < self.size and not self.canceled:
            end = min(start + chunk -1, self.size -1)
            headers['Range'] = 'bytes=%s-%s' % (start, end)
            print("contentlib.PyActiveDataSource.start()2: %s" % (headers['Range'], ))
            with session.get(self.url, headers=headers, params=params, auth=self.auth) as r:
                print("contentlib.PyActiveDataSource.start()3: %s - %s" % (r.status_code, r.headers))
                if r.status_code == requests.codes.partial_content or \
                   r.status_code == requests.codes.ok:
                    self.output.writeBytes(uno.ByteSequence(r.content))
                    start += int(r.headers['Content-Length'])
                    print("contentlib.PyActiveDataSource.start()4 %s" % start)
                else:
                    self.error = 'http error status:%s - headers:%s' % (r.status_code, r.headers)
                    break
        self.output.flush()
        self.output.closeOutput()
        for listener in self.listeners:
            if self.error:
                listener.error(Exception(self.error, self))
            if self.canceled:
                listener.terminated()
            listener.closed()
        print("contentlib.PyActiveDataSource.start()5")
    def terminate(self):
        self.canceled = True


class PyStreamListener(unohelper.Base, XStreamListener):
    def __init__(self, callback=None):
        self.callback = callback
    #XEventListener
    def disposing(self, source):
        pass
    #XStreamListener
    def started(self):
        print("contentlib.PyStreamListener.started()")
    def closed(self):
        if self.callback is not None:
            self.callback()
        print("contentlib.PyStreamListener.closed()")
    def terminated(self):
        print("contentlib.PyStreamListener.terminated()")
    def error(self, e):
        print("contentlib.PyStreamListener.error()")


'''
class PyXCmisDocument(unohelper.Base, XCmisDocument):
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
