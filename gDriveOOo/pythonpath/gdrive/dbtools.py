#!
# -*- coding: utf_8 -*-

import uno

from .unotools import getResourceLocation, getPropertyValue
import datetime

g_url = 'jdbc:hsqldb:%s/%s%s'
g_options = ';default_schema=true;shutdown=true;hsqldb.default_table_type=cached;get_column_name=false'
g_class = 'org.hsqldb.jdbc.JDBCDriver'
g_path = '%s/hsqldb.jar'


def getDbConnection(ctx, scheme, url=None):
    location = getResourceLocation(ctx, 'hsqldb') if url is None else url
    pool = ctx.ServiceManager.createInstance('com.sun.star.sdbc.ConnectionPool')
    url = g_url % (location, scheme, g_options)
    args = (getPropertyValue('JavaDriverClass', g_class), 
            getPropertyValue('JavaDriverClassPath', g_path % location))
    return pool.getConnectionWithInfo(url, args)

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
