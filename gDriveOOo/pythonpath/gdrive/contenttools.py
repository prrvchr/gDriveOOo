#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.beans import UnknownPropertyException, IllegalTypeException
from com.sun.star.uno import Exception as UnoException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE

from .unotools import getProperty, getPropertyValue, createService, getSimpleFile, getResourceLocation
from .items import mergeItem
from .children import updateParent
from .google import g_scheme, getUploadLocation, OutputStream, updateItem, OAuth2Ooo
from .dbtools import unparseDateTime, getItemFromResult

import datetime
import requests
import traceback


def getSession(ctx, username):
    session = requests.Session()
    session.auth = OAuth2Ooo(ctx, username)
    return session

def doSync(ctx, connection, username):
    items = []
    data = ('name', 'createdTime', 'modifiedTime', 'mimeType')
    transform = {'parents': lambda value: value.split(',') if value else None}
    select = connection.prepareCall('CALL "selectSync"(?)')
    select.setLong(1, 4)
    result = select.executeQuery()
    with getSession(ctx, username) as session:
        while result.next():
            items.append(_syncItem(ctx, session, getItemFromResult(result, data, transform)))
    select.close()
    if all(items):
        print("contenttools.doSync(): all -> Ok")
    else:
        print("contenttools.doSync(): all -> Error")
    print("doSync: %s" % items)

def _syncItem(ctx, session, item):
    mode = item['mode']
    if mode & 8 == 8:
        size, stream = _getInputStream(ctx, item['id'])
        if size != 0:
            return uploadItem(ctx, session, item, size, stream)
    elif mode & 4 == 4:
        return updateItem(session, item)
    return False

def uploadItem(ctx, session, item, size, stream):
    location = getUploadLocation(session, item, size)
    if location is not None:
        pump = getPump(ctx)
        pump.setInputStream(stream)
        pump.setOutputStream(OutputStream(session, location, size))
        pump.start()
        return item['id']
    return False
    
def updateData(ctx, content, mode, stream, size):
    identifier = content.getIdentifier()
    item = {'id': identifier.Id, 'parents': [identifier.getParent().Id], 'mode': mode}
    item.update({'Data': getDataContent(content)})
    with getSession(ctx, identifier.UserName) as session:
        return uploadItem(ctx, session, item, size, stream)
    return False

def updateMetaData(ctx, content, mode):
    identifier = content.getIdentifier()
    item = {'id': identifier.Id, 'parents': [identifier.getParent().Id], 'mode': mode}
    item.update({'Data': getDataContent(content)})
    with getSession(ctx, identifier.UserName) as session:
        return updateItem(session, item)
    return False

def getDataContent(content, properties=('Name', 'DateCreated', 'DateModified', 'MimeType')):
    data = {}
    row = getContentProperties(content, properties)
    data['name'] = row.getString(1)
    data['createdTime'] = unparseDateTime(row.getTimestamp(2))
    data['modifiedTime'] = unparseDateTime(row.getTimestamp(3))
    data['mimeType'] = row.getString(4)
    return data

def mergeContent(ctx, connection, event, mode):
    result = False
    identifier = event.Source.getIdentifier()
    if event.PropertyName == 'Id':
        properties = ('Name', 'DateCreated', 'DateModified', 'MimeType','Size',
                      'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable')
        row = getContentProperties(event.Source, properties)
        item = {'Id': identifier.Id}
        item['Name'] = row.getString(1)
        item['DateCreated'] = row.getTimestamp(2)
        item['DateModified'] = row.getTimestamp(3)
        item['MimeType'] = row.getString(4)
        item['Size'] = row.getLong(5)
        if not identifier.IsRoot:
            item['Parents'] = (identifier.getParent().Id, )
        item['CanAddChild'] = row.getBoolean(6)
        item['CanRename'] = row.getBoolean(7)
        item['IsReadOnly'] = row.getBoolean(8)
        item['IsVersionable'] = row.getBoolean(9)
        merge = connection.prepareCall('CALL "mergeItem"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        insert = connection.prepareCall('CALL "insertChild"(?, ?, ?)')
        result = all((mergeItem(merge, identifier.UserId, item), updateParent(insert, item)))
    elif event.PropertyName  == 'Name':
        update = connection.prepareCall('CALL "updateName"(?, ?, ?, ?)')
        update.setString(1, identifier.UserId)
        update.setString(2, identifier.Id)
        update.setString(3, event.NewValue)
        update.execute()
        if update.getLong(4):
            result = True
            if mode == ONLINE:
                result = updateMetaData(ctx, event.Source, 4)
    elif event.PropertyName == 'Size':
        update = connection.prepareCall('CALL "updateSize"(?, ?, ?, ?)')
        update.setString(1, identifier.UserId)
        update.setString(2, identifier.Id)
        update.setLong(3, event.NewValue)
        update.execute()
        result = update.getLong(4)
    elif event.PropertyName == 'SyncMode':
        update = connection.prepareCall('CALL "updateSyncMode"(?, ?, ?, ?)')
        update.setString(1, identifier.UserId)
        update.setString(2, identifier.Id)
        update.setLong(3, event.NewValue)
        update.execute()
        result = update.getLong(4)
        print("contenttools.mergeContent() %s" % result)
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
    #tmp.RemoveFile = False
    return tmp

def getPump(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.io.Pump')

def getPipe(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.io.Pipe')

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

def getUcp(ctx):
    return getUcb(ctx).queryContentProvider('%s://' % g_scheme)

def getMimeType(ctx, stream):
    mimetype = 'application/octet-stream'
    detection = ctx.ServiceManager.createInstance('com.sun.star.document.TypeDetection')
    descriptor = (getPropertyValue('InputStream', stream), )
    format, dummy = detection.queryTypeByDescriptor(descriptor, True)
    if detection.hasByName(format):
        properties = detection.getByName(format)
        for property in properties:
            if property.Name == "MediaType":
                mimetype = property.Value
    return mimetype

def _getInputStream(ctx, id):
    sf = getSimpleFile(ctx)
    url = getResourceLocation(ctx, '%s/%s' % (g_scheme, id))
    if sf.exists(url):
        return sf.getSize(url), sf.openFileRead(url)
    return 0, None
