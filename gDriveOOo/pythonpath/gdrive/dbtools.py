#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.container import NoSuchElementException
from com.sun.star.container import XNameAccess
from com.sun.star.sdbc import XArray
from com.sun.star.sdbc import XResultSet
from com.sun.star.sdbc import XRow

from .unotools import getPropertyValue
from .unotools import getResourceLocation
from .unotools import getSimpleFile


g_protocol = 'jdbc:hsqldb:'
g_folder = 'hsqldb'
g_jar = 'hsqldb.jar'
g_class = 'org.hsqldb.jdbc.JDBCDriver'
g_options = ';default_schema=true;hsqldb.default_table_type=cached;get_column_name=false;ifexists=true'
g_shutdow = ';shutdown=true'


def getDbConnection(ctx, scheme, identifier, shutdown=False):
    service = '/singletons/com.sun.star.deployment.PackageInformationProvider'
    location = ctx.getValueByName(service).getPackageLocation(identifier)
    pool = ctx.ServiceManager.createInstance('com.sun.star.sdbc.ConnectionPool')
    url = _getUrl(location, scheme, shutdown)
    info = _getInfo(location)
    connection = pool.getConnectionWithInfo(url, info)
    return connection
    
def registerDataBase(ctx, scheme, shutdown=False, url=None):
    location = getResourceLocation(ctx, '') if url is None else url
    url = '%s%s.odb' % (location, scheme)
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    if not getSimpleFile(ctx).exists(url):
        _createDataBase(dbcontext, scheme, location, url, shutdown)
    if not dbcontext.hasRegisteredDatabase(scheme):
        dbcontext.registerDatabaseLocation(scheme, url)
    elif dbcontext.getDatabaseLocation(scheme) != url:
        dbcontext.changeDatabaseLocation(scheme, url)
    return url

def _getUrl(location, scheme, shutdown):
    return '%s%s/%s/%s%s%s' % (g_protocol, location, g_folder, scheme, g_options, g_shutdow if shutdown else '')

def _getInfo(location):
    path = '%s/%s/%s' % (location, g_folder, g_jar)
    return (getPropertyValue('JavaDriverClass', g_class), 
            getPropertyValue('JavaDriverClassPath', path))

def _createDataBase(dbcontext, scheme, location, url, shutdown):
    datasource = dbcontext.createInstance()
    datasource.URL = _getUrl(location, scheme, shutdown)
    datasource.Info = _getInfo(location)
    descriptor = (getPropertyValue('Overwrite', True), )
    datasource.DatabaseDocument.storeAsURL(url, descriptor)


class SqlArray(unohelper.Base,
               XArray):
    def __init__(self, values, map):
        self.values = list(values)
        self.map = map
    # XArray
    def getBaseTypeName(self):
        return self.map
    def getBaseType(self):
        return uno.getConstantByName('com.sun.star.sdbc.DataType.%s' % self.map)
    def getArray(self, map):
        return tuple(self.values)
    def getArrayAtIndex(self, index, count, map):
        start = index -1
        end = min(index + count, len(self.values))
        return tuple(self.values[start:end])
    def getResultSet(self, map):
        values = self.getArray(map)
        return ArrayResultSet(values)
    def getResultSetAtIndex(self, index, count, map):
        values = self.getArrayAtIndex(index, count, map)
        return ArrayResultSet(values)


class SqlTypeMap(unohelper.Base,
                 XNameAccess):
    def __init__(self, map='VARCHAR'):
        self.map = map
        self.maps = {'VARCHAR': 'string'}
    # XNameAccess
    def getByName(self, name):
        print("dbtools.SqlTypeMap.getByName() %s" % name)
        if name in self.maps:
            return uno.getTypeByName(self.maps[name])
        raise NoSuchElementException()
    def getElementNames(self):
        names = tuple(self.maps.keys())
        print("dbtools.SqlTypeMap.getElementNames() %s" % (names, ))
        return names
    def hasByName(self, name):
        print("dbtools.SqlTypeMap.hasByName() %s" % name)
        return name in self.maps
    # XElementAccess
    def getElementType(self):
        return uno.getTypeByName(self.maps[self.map])
    def hasElements(self):
        return True


class ArrayResultSet(unohelper.Base,
                     XResultSet,
                     XRow):
    def __init__(self, values):
        self.values = values
        self.count = len(values)
        self.index = 0
    @property
    def value(self):
        if self.index > 0 and self.index <= self.count:
            return self.values[self.index -1]
        return None
    # XResultSet
    def next(self):
        if self.index < self.count:
            self.index += 1
            return True
        return False
    def isBeforeFirst(self):
        return self.count != 0 and self.index == 0
    def isAfterLast(self):
        return self.index == self.count +1
    def isFirst(self):
        return self.index == 1
    def isLast(self):
        return self.index == self.count
    def beforeFirst(self):
        self.index == 0
    def afterLast(self):
        self.index == self.count +1
    def first(self):
        if self.count > 0:
            self.index = 1
            return True
        return False
    def last(self):
        if self.count > 0:
            self.index = self.count
            return True
        return False
    def getRow(self):
        return self.index
    def absolute(self, row):
        if row < 0:
            index = self.count + row +1
            self.index = max(index, 0)
        elif row > 0:
            self.index = min(row, self.count +1)
        return True
    def relative(self, row):
        index = self.index +row
        if row < 0:
            self.index = max(index, 0)
        elif row > 0:
            self.index = min(index, self.count +1)
        return True
    def previous(self):
        if self.index > 1:
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
    # XRow
    def wasNull(self):
        return self.value is None
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
        if index == 1:
            return self.index
        else:
            return self.value


def getItemFromResult(result, data=None, transform=None):
    item = {} if data is None else {'Data':{k: None for k in data}}
    for index in range(1, result.MetaData.ColumnCount +1):
        dbtype = result.MetaData.getColumnTypeName(index)
        name = result.MetaData.getColumnName(index)
        if dbtype == 'VARCHAR':
            value = result.getString(index)
        elif dbtype == 'TIMESTAMP':
            value = result.getTimestamp(index)
        elif dbtype == 'BOOLEAN':
            value = result.getBoolean(index)
        elif dbtype == 'BIGINT' or dbtype == 'SMALLINT':
            value = result.getLong(index)
        else:
            continue
        if transform is not None and name in transform:
            print("dbtools.getItemFromResult() 1: %s: %s" % (name, value))
            value = transform[name](value)
            print("dbtools.getItemFromResult() 2: %s: %s" % (name, value))
        if value is None or result.wasNull():
            continue
        if data is not None and name in data:
            item['Data'][name] = value
        else:
            item[name] = value
    return item
