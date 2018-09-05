#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.beans import UnknownPropertyException, IllegalTypeException
from com.sun.star.uno import Exception as UnoException

from .unotools import getProperty, getPropertyValue, createService
from .items import mergeItem
from .children import updateParent
from .identifiers import updateIdentifier
from .google import getUploadLocation, OutputStream

import datetime
import requests
import traceback


def uploadItem(ctx, inputstream, identifier, name, size, mediatype, new=False):
    location, session = getUploadLocation(ctx, identifier, name, size, mediatype, new)
    if location is not None:
        pump = getPump(ctx)
        pump.setInputStream(inputstream)
        output = OutputStream(ctx, session, identifier, location, size)
        pump.setOutputStream(output)
        pump.start()

def createNewContent(ctx, statement, identifier, contentinfo):
    print("contenttools._createNewContent()")
    item = {'Identifier': getUcb(ctx).createContentIdentifier('%s#' % identifier)}
    if contentinfo.Type == 'application/vnd.google-apps.folder':
        item.update({'Statement': statement})
        name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'
    elif contentinfo.Type == 'application/vnd.oasis.opendocument':
        name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveOfficeContent'
    return createService(name, ctx, **item)

def mergeContent(ctx, connection, event, root, user):
    result = False
    if event.PropertyName == 'Id':
        properties = ('Identifier', 'Name', 'DateCreated', 'DateModified', 'MediaType',
                      'IsReadOnly', 'CanRename', 'IsFolder', 'Size', 'IsVersionable')
        row = getContentProperties(event.Source, properties)
        identifier = row.getObject(1, None)
        item = {'Id': event.NewValue}
        item['Name'] = row.getString(2)
        item['DateCreated'] = row.getTimestamp(3)
        item['DateModified'] = row.getTimestamp(4)
        item['MediaType'] = row.getString(5)
        item['IsReadOnly'] = row.getBoolean(6)
        item['CanRename'] = row.getBoolean(7)
        item['IsFolder'] = row.getBoolean(8)
        item['Size'] = row.getLong(9)
        item['IsVersionable'] = row.getBoolean(10)
        item['Parents'] = (identifier.getParent().Id, )
        merge = connection.prepareCall('CALL "mergeItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        insert = connection.prepareCall('CALL "insertChild"(?, ?, ?)')
        result = all((mergeItem(merge, item), updateParent(insert, item), updateIdentifier(connection, identifier.UserName, event.NewValue)))
    elif event.PropertyName  == 'Name':
        id = getContentProperties(event.Source, ('Id', )).getString(1)
        update = connection.prepareCall('CALL "updateName"(?, ?, ?)')
        update.setString(1, id)
        update.setString(2, event.NewValue)
        update.execute()
        result = update.getLong(3)
    elif event.PropertyName == 'WhoWrite':
        id = getContentProperties(event.Source, ('Id', )).getString(1)
        update = connection.prepareCall('CALL "updateWhoWrite"(?, ?, ?)')
        update.setString(1, id)
        update.setString(2, event.NewValue)
        update.execute()
        result = update.getLong(3)
    elif event.PropertyName == 'Size':
        id = getContentProperties(event.Source, ('Id', )).getString(1)
        update = connection.prepareCall('CALL "updateSize"(?, ?, ?)')
        update.setString(1, id)
        update.setLong(2, event.NewValue)
        update.execute()
        result = update.getLong(3)
    elif event.PropertyName  == 'IsRead':
        id = getContentProperties(event.Source, ('Id', )).getString(1)
        update = connection.prepareCall('CALL "updateIsRead"(?, ?, ?)')
        update.setString(1, id)
        update.setBoolean(2, event.NewValue)
        update.execute()
        result = update.getLong(3)
    return result

def propertyChange(source, name, oldvalue, newvalue):
    if name in source.propertiesListener:
        events = (_getPropertyChangeEvent(source, name, oldvalue, newvalue), )
        for listener in source.propertiesListener[name]:
            listener.propertiesChange(events)

def getPropertiesValues(source, properties, logger):
    namedvalues = []
    for property in properties:
        value = None
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
        msg = "ERROR: Requested property: %s as incorect type" % property
        if hasattr(property, 'Name') and hasattr(source, property.Name):
            value = getattr(source, property.Name)
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            msg = "Get property: %s value: %s" % (property.Name, value)
        else:
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
            msg = "ERROR: Requested property: %s is not available" % property.Name
        logger.logp(level, source.__class__.__name__, "getPropertiesValues()", msg)
        print("%s.getPropertiesValues() %s" % (source.__class__.__name__, msg))
        namedvalues.append(uno.createUnoStruct('com.sun.star.beans.NamedValue', property.Name, value))
    return tuple(namedvalues)

def setPropertiesValues(source, properties, logger):
    results = []
    for property in properties:
        result = UnoException('SetProperty Exception', source)
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.SEVERE")
        msg = "ERROR: Requested property: %s as incorect type" % property
        if hasattr(property, 'Name') and hasattr(property, 'Value'):
            if hasattr(source, property.Name):
                setattr(source, property.Name, property.Value)
                result = None
                level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
                msg = "Set property: %s value: %s" % (property.Name, property.Value)
            else:
                result = UnknownPropertyException('UnknownProperty: %s' % property.Name, source)
                msg = "ERROR: Requested property: %s is not available" % property.Name
        logger.logp(level, source.__class__.__name__, "setPropertiesValues()", msg)
        print("%s.setPropertiesValues() %s" % (source.__class__.__name__, msg))
        results.append(result)
    return tuple(results)

def getContentProperties(content, names):
    properties = []
    for name in names:
        properties.append(getProperty(name))
    command = getCommand('getPropertyValues', tuple(properties))
    return content.execute(command, 0, None)

def setContentProperties(content, arguments):
    properties = []
    for name, value in arguments.items():
        properties.append(getPropertyValue(name, value))
    command = getCommand('setPropertyValues', tuple(properties))
    return content.execute(command, 0, None)

def getId(uri, root=''):
    id = ''
    count = uri.getPathSegmentCount()
    if count > 0:
        id = uri.getPathSegment(count -1).strip()
    if count < 2 and id == "":
        id = root
    return id

def getParentUri(ctx, uri):
    path = _getParentPath(uri)
    identifier = '%s://%s/%s' % (uri.getScheme(), uri.getAuthority(), '/'.join(path))
    return getUri(ctx, identifier)

def _getParentPath(uri):
    paths = []
    count = uri.getPathSegmentCount()
    if count > 0:
        for i in range(count -1):
            paths.append(uri.getPathSegment(i).strip())
    return tuple(paths)

def _getPropertyChangeEvent(source, name, oldvalue, newvalue, further=False, handle=-1):
    event = uno.createUnoStruct('com.sun.star.beans.PropertyChangeEvent')
    event.Source = source
    event.PropertyName = name
    event.Further = further
    event.PropertyHandle = handle
    event.OldValue = oldvalue
    event.NewValue = newvalue
    return event

def getCmisProperty(id, name, unotype, updatable, required, multivalued, openchoice, choices, value):
    property = uno.createUnoStruct('com.sun.star.document.CmisProperty')
    property.Id = id
    property.Name = name
    property.Type = unotype
    property.Updatable = updatable
    property.Required = required
    property.MultiValued = multivalued
    property.OpenChoice = openchoice
    property.Choices = choices
    property.Value = value
    return property

def getTempFile(ctx):
    tmp = ctx.ServiceManager.createInstance('com.sun.star.io.TempFile')
    tmp.RemoveFile = False
    return tmp

def getPump(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.io.Pump')

def getPipe(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.io.Pipe')

def getContent(ctx, identifier):
    return getUcb(ctx).queryContent(identifier)

def getContentEvent(action, content, id):
    event = uno.createUnoStruct('com.sun.star.ucb.ContentEvent')
    event.Action = action
    event.Content = content
    event.Id = id
    return event

def getCommand(name, argument, handle=-1):
    command = uno.createUnoStruct('com.sun.star.ucb.Command')
    command.Name = name
    command.Handle = handle
    command.Argument = argument
    return command

def getCommandInfo(name, typename=None, handle=-1):
    command = uno.createUnoStruct('com.sun.star.ucb.CommandInfo')
    command.Name = name
    command.Handle = handle
    if typename is not None:
        command.ArgType = uno.getTypeByName(typename)
    return command

def getContentInfo(ctype, attributes, properties):
    info = uno.createUnoStruct('com.sun.star.ucb.ContentInfo',
                                ctype,
                                attributes,
                                properties)
    return info

def getUri(ctx, identifier):
    factory = ctx.ServiceManager.createInstance('com.sun.star.uri.UriReferenceFactory')
    return factory.parse(identifier)

def getUcb(ctx, arguments=None):
    if arguments is None:
        arguments = ('Local', 'Office')
    name = 'com.sun.star.ucb.UniversalContentBroker'
    return ctx.ServiceManager.createInstanceWithArguments(name, (arguments, ))

def getUcp(ctx, identifier):
    return getUcb(ctx).queryContentProvider(identifier)
