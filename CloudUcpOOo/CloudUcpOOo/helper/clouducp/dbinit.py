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
        logMessage(ctx, INFO, "Stage 1", 'dbinit', 'getDataSourceUrl()')
        location = getResourceLocation(ctx, plugin, g_path)
        logMessage(ctx, INFO, "Stage 2", 'dbinit', 'getDataSourceUrl()')
        url = '%s/%s.odb' % (location, dbname)
        logMessage(ctx, INFO, "Stage 3", 'dbinit', 'getDataSourceUrl()')
        if not getSimpleFile(ctx).exists(url):
            logMessage(ctx, INFO, "Stage 4", 'dbinit', 'getDataSourceUrl()')
            error = _createDataSource(ctx, dbctx, url, location, dbname)
            logMessage(ctx, INFO, "Stage 5", 'dbinit', 'getDataSourceUrl()')
            if register and error is None:
                logMessage(ctx, INFO, "Stage 6", 'dbinit', 'getDataSourceUrl()')
                registerDataSource(dbctx, dbname, url)
        logMessage(ctx, INFO, "Stage 7", 'dbinit', 'getDataSourceUrl()')
        return url, error
    except Exception as e:
        msg = "getDataSourceUrl: ERROR: %s - %s" % (e, traceback.print_exc())
        logMessage(ctx, SEVERE, msg, 'dbinit', 'getDataSourceUrl()')


def _createDataSource(ctx, dbcontext, url, location, dbname):
    datasource = dbcontext.createInstance()
    datasource.URL = getDataSourceLocation(location, dbname, False)
    datasource.Info = getDataSourceInfo() + getDataSourceJavaInfo(location)
    datasource.DatabaseDocument.storeAsURL(url, ())
    error = _createDataBase(ctx, datasource)
    datasource.DatabaseDocument.store()
    return error

def _createDataBase(ctx, datasource):
    #connection, error = getDataSourceConnection(datasource)
    logMessage(ctx, INFO, "Stage 1", 'dbinit', '_createDataBase()')
    error = None
    try:
        logMessage(ctx, INFO, "Stage 2", 'dbinit', '_createDataBase()')
        connection = datasource.getConnection('', '')
    except Exception as e:
        error = e
        msg = "_createDataBase: ERROR: %s - %s" % (e, traceback.print_exc())
        logMessage(ctx, SEVERE, msg, 'dbinit', '_createDataBase()')
    if error is not None:
        logMessage(ctx, INFO, "Stage 3", 'dbinit', '_createDataBase()')
        return error
    logMessage(ctx, INFO, "Stage 4", 'dbinit', '_createDataBase()')
    error = checkDataBase(connection)
    logMessage(ctx, INFO, "Stage 5", 'dbinit', '_createDataBase()')
    if error is None:
        logMessage(ctx, INFO, "Stage 6", 'dbinit', '_createDataBase()')
        statement = connection.createStatement()
        logMessage(ctx, INFO, "Stage 7", 'dbinit', '_createDataBase()')
        _createStaticTable(statement, _getStaticTables())
        tables, statements = getTablesAndStatements(statement)
        _executeQueries(statement, tables)
        logMessage(ctx, INFO, "Stage 8", 'dbinit', '_createDataBase()')
        executeQueries(statement, _getViews())
    connection.close()
    connection.dispose()
    logMessage(ctx, INFO, "Stage 9", 'dbinit', '_createDataBase()')
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
