#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.beans import UnknownPropertyException, IllegalTypeException
from com.sun.star.uno import Exception as UnoException

from .unotools import getProperty, getPropertyValue, createService
from .items import mergeItem
from .children import updateParent
from .identifiers import updateIdentifier
from .google import getUploadLocation, OutputStream, OAuth2Ooo
from .dbtools import unparseDateTime

import datetime
import requests
import traceback


def getSession(ctx, scheme, username):
    session = requests.Session()
    session.auth = OAuth2Ooo(ctx, scheme, username)
    return session

def uploadItem(ctx, session, stream, content, id, size, new=False):
    data, headers = None, {'X-Upload-Content-Length': '%s' % size}
    if new:
        data = {}
        row = getContentProperties(content, ('Name', 'DateCreated', 'DateModified', 'MediaType'))
        headers['X-Upload-Content-Type'] = row.getString(4)
        data['name'] = row.getString(1)
        data['createdTime'] = unparseDateTime(row.getTimestamp(2))
        data['modifiedTime'] = unparseDateTime(row.getTimestamp(3))
        data['parents'] = [content.getIdentifier().getParent().Id]
    session.headers.update(headers)
    location = getUploadLocation(session, id, data)
    if location is not None:
        pump = getPump(ctx)
        pump.setInputStream(stream)
        pump.setOutputStream(OutputStream(session, location, size))
        pump.start()

def createNewContent(ctx, statement, identifier, contentinfo, title):
    try:
        print("contenttools._createNewContent() 1")
        id = getUcb(ctx).createContentIdentifier('%s#' % identifier)
        item = {'Identifier': id}
        if contentinfo.Type == 'application/vnd.google-apps.folder':
            item.update({'Statement': statement})
            name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'
        elif contentinfo.Type == 'application/vnd.oasis.opendocument':
            item.update({'Name': title})
            name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveOfficeContent'
        content = createService(name, ctx, **item)
        print("contenttools._createNewContent() 2")
        return content
    except Exception as e:
        print("contenttools.createNewContent().Error: %s - %s" % (e, traceback.print_exc()))

def mergeContent(ctx, connection, event, userid):
    result = False
    if event.PropertyName == 'Id':
        properties = ('Name', 'DateCreated', 'DateModified', 'MediaType','Size',
                      'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable')
        row = getContentProperties(event.Source, properties)
        item = {'Id': event.NewValue}
        item['Name'] = row.getString(1)
        item['DateCreated'] = row.getTimestamp(2)
        item['DateModified'] = row.getTimestamp(3)
        item['MediaType'] = row.getString(4)
        item['Size'] = row.getLong(5)
        item['Parents'] = (event.Source.getIdentifier().getParent().Id, )
        item['CanAddChild'] = row.getBoolean(6)
        item['CanRename'] = row.getBoolean(7)
        item['IsReadOnly'] = row.getBoolean(8)
        item['IsVersionable'] = row.getBoolean(9)
        merge = connection.prepareCall('CALL "mergeItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        insert = connection.prepareCall('CALL "insertChild"(?, ?, ?)')
        result = all((mergeItem(merge, userid, item),
                      updateParent(insert, item),
                      updateIdentifier(connection, userid, event.NewValue)))
    elif event.PropertyName  == 'Name':
        update = connection.prepareCall('CALL "updateName"(?, ?, ?)')
        update.setString(1, event.Source.getIdentifier().Id)
        update.setString(2, event.NewValue)
        update.execute()
        result = update.getLong(3)
    elif event.PropertyName == 'Size':
        update = connection.prepareCall('CALL "updateSize"(?, ?, ?)')
        update.setString(1, event.Source.getIdentifier().Id)
        update.setLong(2, event.NewValue)
        update.execute()
        result = update.getLong(3)
    elif event.PropertyName  == 'IsRead':
        update = connection.prepareCall('CALL "updateIsRead"(?, ?, ?)')
        update.setString(1, event.Source.getIdentifier().Id)
        update.setBoolean(2, event.NewValue)
        update.execute()
        result = update.getLong(3)
    elif event.PropertyName == 'IsWrite':
        update = connection.prepareCall('CALL "updateIsWrite"(?, ?, ?, ?)')
        update.setString(1, userid)
        update.setString(2, event.Source.getIdentifier().Id)
        update.setBoolean(3, event.NewValue)
        update.execute()
        result = update.getLong(4)
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

def getParentId(identifier):
    paths = []
    while not identifier.IsRoot:
        paths.append(identifier.Id)
        identifier = identifier.getParent()
    paths.append(identifier.Id)
    return tuple(paths)

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
