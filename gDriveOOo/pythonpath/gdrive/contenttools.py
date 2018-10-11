#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.beans import UnknownPropertyException, IllegalTypeException
from com.sun.star.uno import Exception as UnoException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
from com.sun.star.ucb.ContentAction import INSERTED, REMOVED, DELETED, EXCHANGED

from .unotools import getProperty, getPropertyValue, createService, getSimpleFile, getResourceLocation
#from .items import getMergeCall, mergeItem, setContentCall
from .google import unparseDateTime, g_scheme, getUploadLocation, OutputStream, updateItem, OAuth2Ooo
from .google import ACQUIRED, CREATED, RENAMED, REWRITED, MODIFIED, TRASHED
from .google import getDataFromItem
from .dbtools import getItemFromResult

import datetime
import requests
import traceback


def notifyContentListener(ctx, content, action):
    identifier = content.getIdentifier()
    if action == INSERTED or action == REMOVED:
        parent = identifier.getParent()
        event = getContentEvent(action, content, parent)
        getUcb(ctx).queryContent(parent).notify(event)
    elif action == DELETED:
        event = getContentEvent(action, content, identifier)
        content.notify(event)
        notifyContentListener(ctx, content, REMOVED)
    elif action == EXCHANGED:
        #event = getContentEvent(action, content, identifier)
        #content.notify(event)
        notifyContentListener(ctx, content, DELETED)
        notifyContentListener(ctx, content, INSERTED)

def getSession(ctx, username):
    session = requests.Session()
    session.auth = OAuth2Ooo(ctx, username)
    return session

def doSync(ctx, connection, username):
    items = []
    #data = ('name', 'createdTime', 'modifiedTime', 'mimeType')
    transform = {'parents': lambda value: value.split(',') if value else None}
    select = connection.prepareCall('CALL "selectSync"(?)')
    select.setLong(1, ACQUIRED)
    result = select.executeQuery()
    with getSession(ctx, username) as session:
        while result.next():
            items.append(_syncItem(ctx, session, getItemFromResult(result, None, transform)))
    select.close()
    if items and all(items):
        update = connection.prepareCall('CALL "updateSync"(?, ?, ?)')
        update.setString(1, ','.join(items))
        update.setLong(2, ACQUIRED)
        update.execute()
        r = update.getLong(3)
        print("contenttools.doSync(): all -> Ok %s" % r)
    else:
        print("contenttools.doSync(): all -> Error")
    print("doSync: %s" % items)
    return all(items)

def _syncItem(ctx, session, item):
    result = False
    mode, id, data = getDataFromItem(item)
    if mode & REWRITED:
        size, stream = _getInputStream(ctx, id)
        if size != 0:
            result = uploadItem(ctx, session, id, data, size, stream)
    elif mode & MODIFIED:
        result = updateItem(session, id, data)
    if result and mode & TRASHED:
        result = updateItem(session, id, {'trashed': True})
    return result

def uploadItem(ctx, session, id, data, size, stream):
    location = getUploadLocation(session, id, data, size)
    if location is not None:
        pump = getPump(ctx)
        pump.setInputStream(stream)
        pump.setOutputStream(OutputStream(session, location, size))
        pump.start()
        return id
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
    print("contenttools.mergeContent() %s - %s" % (event.PropertyName, event.NewValue))
    result = False
    identifier = event.Source.getIdentifier()
    if event.PropertyName == 'Id':
        properties = ('Name', 'DateCreated', 'DateModified', 'MimeType', 'Size', 'Trashed',
                      'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable', 'Loaded')
        row = getContentProperties(event.Source, properties)
        mode = event.NewValue
        insert = insertContentItemCall(connection)
        insert.setString(1, identifier.UserId)
        insert.setString(2, identifier.Id)
        insert.setString(3, identifier.getParent().Id)
        insert.setString(4, mode)
        result = insertContentItem(insert, row, properties, 5)
    elif event.PropertyName  == 'Name':
        update = connection.prepareCall('CALL "updateName"(?, ?, ?, ?, ?)')
        update.setString(1, identifier.UserId)
        update.setString(2, identifier.Id)
        update.setString(3, event.NewValue)
        update.setLong(4, RENAMED+MODIFIED)
        update.execute()
        result = update.getLong(5)
    elif event.PropertyName == 'Size':
        update = connection.prepareCall('CALL "updateSize"(?, ?, ?, ?, ?)')
        update.setString(1, identifier.UserId)
        update.setString(2, identifier.Id)
        update.setLong(3, event.NewValue)
        update.setLong(4, REWRITED)
        update.execute()
        result = update.getLong(5)
    elif event.PropertyName == 'Trashed':
        update = connection.prepareCall('CALL "updateTrashed"(?, ?, ?, ?, ?)')
        update.setString(1, identifier.UserId)
        update.setString(2, identifier.Id)
        update.setLong(3, event.NewValue)
        update.setLong(4, TRASHED)
        update.execute()
        result = update.getLong(5)
    elif event.PropertyName == 'Loaded':
        update = connection.prepareCall('CALL "updateLoaded"(?, ?, ?, ?)')
        update.setString(1, identifier.UserId)
        update.setString(2, identifier.Id)
        update.setLong(3, event.NewValue)
        update.execute()
        return update.getLong(4)
    if result and mode == ONLINE:
        result = doSync(ctx, connection, identifier.UserName)
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

def getContentProperties(content, properties):
    properties = []
    for name in properties:
        properties.append(getProperty(name))
    command = getCommand('getPropertyValues', tuple(properties))
    return content.execute(command, 0, None)

def getContentData(content, properties):
    rows = getContentProperties(content, properties)
    index, data = 1, {}
    for name in properties:
        data[name] = rows.getObject(index, None)
        index += 1
    return data

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
