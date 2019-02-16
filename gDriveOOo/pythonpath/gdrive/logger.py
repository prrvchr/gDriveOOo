#!
# -*- coding: utf_8 -*-

import uno

from .unotools import getConfiguration


def getLogger(ctx=None, logger='org.openoffice.logging.DefaultLogger'):
    if ctx is None:
        ctx = uno.getComponentContext()
    return ctx.getValueByName('/singletons/com.sun.star.logging.LoggerPool').getNamedLogger(logger)

def getLoggerSetting(ctx, logger='org.openoffice.logging.DefaultLogger'):
    enabled, index = _getLogIndex(ctx, logger)
    handler = _getLogHandler(ctx, logger)
    return enabled, index, handler

def setLoggerSetting(ctx, enabled, index, handler, logger='org.openoffice.logging.DefaultLogger'):
    _setLogIndex(ctx, enabled, index, logger)
    _setLogHandler(ctx, handler, None, logger)

def getLoggerUrl(ctx, logger='org.openoffice.logging.DefaultLogger'):
    url = '$(userurl)/$(loggername).log'
    settings = _getLoggerConfiguration(ctx, logger).getByName('HandlerSettings')
    if settings.hasByName('FileURL'):
        url = settings.getByName('FileURL')
    service = ctx.ServiceManager.createInstance('com.sun.star.util.PathSubstitution')
    return service.substituteVariables(url.replace('$(loggername)', logger), True)

def _getLogIndex(ctx, logger='org.openoffice.logging.DefaultLogger'):
    index = 7
    level = _getLoggerConfiguration(ctx, logger).LogLevel
    enabled = level != uno.getConstantByName('com.sun.star.logging.LogLevel.OFF')
    if enabled:
        index = _getLogLevels().index(level)
    return enabled, index

def _setLogIndex(ctx, enabled, index, logger='org.openoffice.logging.DefaultLogger'):
    level = uno.getConstantByName('com.sun.star.logging.LogLevel.OFF')
    if enabled:
        level = _getLogLevels()[index]
    configuration = _getLoggerConfiguration(ctx, logger)
    configuration.LogLevel = level
    configuration.commitChanges()

def _getLogHandler(ctx, logger='org.openoffice.logging.DefaultLogger'):
    handler = _getLoggerConfiguration(ctx, logger).DefaultHandler
    return 1 if handler != 'com.sun.star.logging.FileHandler' else 2

def _setLogHandler(ctx, handler, option=None, logger='org.openoffice.logging.DefaultLogger'):
    if handler:
        _logToConsole(ctx, option, logger)
    else:
        _logToFile(ctx, option, logger)

def _getLogLevels():
    levels = (uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE'),
              uno.getConstantByName('com.sun.star.logging.LogLevel.WARNING'),
              uno.getConstantByName('com.sun.star.logging.LogLevel.INFO'),
              uno.getConstantByName('com.sun.star.logging.LogLevel.CONFIG'),
              uno.getConstantByName('com.sun.star.logging.LogLevel.FINE'),
              uno.getConstantByName('com.sun.star.logging.LogLevel.FINER'),
              uno.getConstantByName('com.sun.star.logging.LogLevel.FINEST'),
              uno.getConstantByName('com.sun.star.logging.LogLevel.ALL'))
    return levels

def _getLoggerConfiguration(ctx, logger='org.openoffice.logging.DefaultLogger'):
    nodepath = '/org.openoffice.Office.Logging/Settings'
    configuration = getConfiguration(ctx, nodepath, True)
    if not configuration.hasByName(logger):
        configuration.insertByName(logger, configuration.createInstance())
        configuration.commitChanges()
    nodepath += '/%s' % logger
    return getConfiguration(ctx, nodepath, True)

def _logToConsole(ctx, threshold=None, logger='org.openoffice.logging.DefaultLogger'):
    configuration = _getLoggerConfiguration(ctx, logger)
    configuration.DefaultHandler = 'com.sun.star.logging.ConsoleHandler'
    if threshold is not None:
        settings = configuration.getByName('HandlerSettings')
        if settings.hasByName('Threshold'):
            settings.replaceByName('Threshold', threshold)
        else:
            settings.insertByName('Threshold', threshold)
    configuration.commitChanges()

def _logToFile(ctx, url=None, logger='org.openoffice.logging.DefaultLogger'):
    configuration = _getLoggerConfiguration(ctx, logger)
    configuration.DefaultHandler = 'com.sun.star.logging.FileHandler'
    if url is not None:
        settings = configuration.getByName('HandlerSettings')
        if settings.hasByName('FileURL'):
            settings.replaceByName('FileURL', url)
        else:
            settings.insertByName('FileURL', url)
    configuration.commitChanges()
