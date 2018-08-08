#!
# -*- coding: utf_8 -*-

import uno


g_protocol = 'jdbc:hsqldb:'
g_class = 'org.hsqldb.jdbc.JDBCDriver'
g_path = 'hsqldb/'
g_jar = 'hsqldb.jar'
g_dbname = 'vnd.google-apps'
g_options = ';default_schema=true;hsqldb.default_table_type=cached;get_column_name=false;ifexists=true'


def setDataBaseConnection(*arg):
    doc = XSCRIPTCONTEXT.getDocument()
    ctx = XSCRIPTCONTEXT.getComponentContext()
    url = _getDocumentUrlPath(ctx, doc)
    doc.DataSource.Settings.JavaDriverClass = g_class
    doc.DataSource.Settings.JavaDriverClassPath = url + g_path + g_jar
    doc.DataSource.URL = g_protocol + url + g_path + g_dbname + g_options

def _getDocumentUrlPath(ctx, doc):
    url = uno.createUnoStruct('com.sun.star.util.URL')
    url.Complete = doc.URL
    dummy, url = ctx.ServiceManager.createInstanceWithContext('com.sun.star.util.URLTransformer', ctx).parseStrict(url)
    return url.Protocol + url.Path


g_exportedScripts = (setDataBaseConnection, )
