#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.sdbc import XDataSource, XArray, XRow, XResultSet
from com.sun.star.lang import IllegalArgumentException

from .unotools import getResourceLocation, getPropertyValue
import datetime
import traceback

g_class = 'org.hsqldb.jdbc.JDBCDriver'
g_jar = 'hsqldb.jar'
g_protocol = 'jdbc:hsqldb:'
g_path = 'hsqldb/'
g_scheme = 'vnd.google-apps'
#g_options = ';default_schema=true;shutdown=true;hsqldb.default_table_type=cached;get_column_name=false'
g_options = ';default_schema=true;hsqldb.default_table_type=cached;get_column_name=false;ifexists=true'


def getDbConnection(ctx, scheme, shutdown=False, url=None):
    location = getResourceLocation(ctx, g_path) if url is None else url
    pool = ctx.ServiceManager.createInstance('com.sun.star.sdbc.ConnectionPool')
    url = g_protocol + location + scheme + g_options
    if shutdown:
        url += ';shutdown=true'
    args = (getPropertyValue('JavaDriverClass', g_class), 
            getPropertyValue('JavaDriverClassPath', location + g_jar))
    connection = pool.getConnectionWithInfo(url, args)
    return connection


class SqlArray(unohelper.Base, XArray):
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


class ArrayResultSet(unohelper.Base, XResultSet, XRow):
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


def getItemFromResult(result):
    item = {}
    for index in range(1, result.MetaData.ColumnCount +1):
        dbtype = result.MetaData.getColumnTypeName(index)
        if dbtype == 'VARCHAR':
            value = result.getString(index)
        elif dbtype == 'TIMESTAMP':
            value = result.getTimestamp(index)
        elif dbtype == 'BOOLEAN':
            value = result.getBoolean(index)
        elif dbtype == 'BIGINT':
            value = result.getLong(index)
        else:
            value = result.getObject(index, None)
        if result.wasNull():
            value = None
        item[result.MetaData.getColumnName(index)] = value
    return item

def setDbContext(ctx, scheme):
    dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
    if dbcontext.hasRegisteredDatabase(scheme):
        #if dbcontext.getDatabaseLocation(scheme) != url:
        print("getDbConnection url changed; %s" % dbcontext.getDatabaseLocation(scheme)) 
    else:
        print("getDbConnection url changed")
        datasource = dbcontext.createInstance()
        dbcontext.registerObject(scheme, datasource) # datasource need to be a XDocumentDataSource
        datasource.URL = url
        datasource.Info = args
        print("getDbConnection url changed; %s" % dbcontext.getDatabaseLocation(scheme))
    #mri = ctx.ServiceManager.createInstance('mytools.Mri')
    #mri.inspect(pool.getDriverByURL(url))
    #mri.inspect(pool.getDriverByURL(url))

def getMarks(fields):
    marks = []
    for field in fields:
        marks.append('?')
    return marks

def getFieldMarks(fields):
    marks = []
    for field in fields:
        marks.append('%s = ?' % field)
    return marks

def parseDateTime(timestr=None, format=u'%Y-%m-%dT%H:%M:%S.%fZ'):
    if timestr is None:
        t = datetime.datetime.now()
    else:
        t = datetime.datetime.strptime(timestr, format)
    return _getDateTime(t.microsecond, t.second, t.minute, t.hour, t.day, t.month, t.year)

def unparseDateTime(t):
    timestr = '%s-%s-%sT%s:%s:%s' % (t.Year, t.Month, t.Day, t.Hours, t.Minutes, t.Seconds)
    if hasattr(t, 'HundredthSeconds'):
        timestr += '.%sZ' % t.HundredthSeconds * 10
    elif hasattr(t, 'NanoSeconds'):
        timestr += '.%sZ' % t.NanoSeconds // 1000000
    return timestr

def _getDateTime(microsecond=0, second=0, minute=0, hour=0, day=1, month=1, year=1970, utc=True):
    t = uno.createUnoStruct('com.sun.star.util.DateTime')
    t.Year = year
    t.Month = month
    t.Day = day
    t.Hours = hour
    t.Minutes = minute
    t.Seconds = second
    if hasattr(t, 'HundredthSeconds'):
        t.HundredthSeconds = microsecond // 10000
    elif hasattr(t, 'NanoSeconds'):
        t.NanoSeconds = microsecond * 1000
    if hasattr(t, 'IsUTC'):
        t.IsUTC = utc
    return t
