#!
# -*- coding: utf_8 -*-

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from unolib import getResourceLocation
from unolib import getSimpleFile

from .dbconfig import g_path
from .dbqueries import getSqlQuery
from .dbtools import getTablesAndStatements
from .dbtools import registerDataSource
from .dbtools import executeQueries
from .dbtools import getDataSourceLocation
from .dbtools import getDataSourceInfo
from .dbtools import getDataSourceJavaInfo
from .dbtools import getDataSourceConnection
from .dbtools import checkDataBase
from .logger import logMessage

import traceback


def getDataSourceUrl(ctx, dbctx, dbname, plugin, register):
    try:
        error = None
        location = getResourceLocation(ctx, plugin, g_path)
        url = '%s/%s.odb' % (location, dbname)
        if not getSimpleFile(ctx).exists(url):
            error = _createDataSource(ctx, dbctx, url, location, dbname)
            if register and error is None:
                registerDataSource(dbctx, dbname, url)
        return url, error
    except Exception as e:
        msg = "getDataSourceUrl: ERROR: %s - %s" % (e, traceback.print_exc())
        logMessage(ctx, SEVERE, msg, 'dbinit', 'getDataSourceUrl()')


def _createDataSource(ctx, dbcontext, url, location, dbname):
    datasource = dbcontext.createInstance()
    datasource.URL = getDataSourceLocation(location, dbname, False)
    datasource.Info = getDataSourceInfo() + getDataSourceJavaInfo(location)
    datasource.DatabaseDocument.storeAsURL(url, ())
    error = _createDataBase(datasource)
    datasource.DatabaseDocument.store()
    return error

def _createDataBase(datasource):
    connection, error = getDataSourceConnection(datasource)
    if error is not None:
        return error
    error = checkDataBase(connection)
    if error is None:
        print("dbinit._createDataBase()")
        statement = connection.createStatement()
        _createStaticTable(statement, _getStaticTables())
        tables, statements = getTablesAndStatements(statement)
        _executeQueries(statement, tables)
        executeQueries(statement, _getViews())
    connection.close()
    connection.dispose()
    return error

def _createStaticTable(statement, tables):
    for table in tables:
        query = getSqlQuery('createTable' + table)
        print("dbtool._createStaticTable(): %s" % query)
        statement.executeQuery(query)
    for table in tables:
        statement.executeQuery(getSqlQuery('setTableSource', table))
        statement.executeQuery(getSqlQuery('setTableReadOnly', table))

def _executeQueries(statement, queries):
    for query in queries:
        statement.executeQuery(query)

def _getStaticTables():
    tables = ('Tables',
              'Columns',
              'TableColumn',
              'Settings')
    return tables

def _getViews():
    return ('createItemView',
            'createChildView',
            'createSyncView')
