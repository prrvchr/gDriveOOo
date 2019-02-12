#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.beans import UnknownPropertyException, IllegalTypeException, PropertyVetoException
from com.sun.star.lang import IllegalAccessException
from com.sun.star.ucb import NameClashResolveRequest, IllegalIdentifierException, InteractiveNetworkOffLineException
from com.sun.star.ucb import InteractiveNetworkReadException, UnsupportedNameClashException
from com.sun.star.ucb import NameClashException, AuthenticationRequest, URLAuthenticationRequest
from com.sun.star.sdb import ParametersRequest
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
from com.sun.star.ucb.ContentAction import INSERTED, REMOVED, DELETED, EXCHANGED

from .unotools import getProperty, getPropertyValue, createService, getSimpleFile, getResourceLocation
#from .items import getMergeCall, mergeItem, setContentCall
from .google import unparseDateTime, g_scheme, getUploadLocation, OutputStream, updateItem, OAuth2Ooo
from .google import ACQUIRED, CREATED, RENAMED, REWRITED, TRASHED
from .google import g_folder, g_link, g_doc
from .dbtools import getItemFromResult

import datetime
import requests
import traceback

g_OfficeDocument = 'application/vnd.oasis.opendocument'


def createContent(ctx, data):
    name, content = None, None
    mime = data.get('MimeType', 'application/octet-stream')
    if mime == g_folder:
        name = 'DriveFolderContent'
    elif mime == g_link:
        pass
    elif mime.startswith(g_doc):
        name = 'DriveDocumentContent'
    elif mime.startswith(g_OfficeDocument):
        name = 'DriveOfficeContent'
    if name is not None:
        content = createService('com.gmail.prrvchr.extensions.gDriveOOo.%s' % name, ctx, **data)
    return content

def getSession(ctx, username):
    session = requests.Session()
    session.auth = OAuth2Ooo(ctx, username)
    return session

def doSync(ctx, identifier):
    items = []
    #data = ('name', 'createdTime', 'modifiedTime', 'mimeType')
    transform = {'parents': lambda value: value.split(',')}
    select = identifier.Connection.prepareCall('CALL "selectSync"(?)')
    select.setLong(1, ACQUIRED)
    result = select.executeQuery()
    with getSession(ctx, identifier.User.Name) as session:
        while result.next():
            item = getItemFromResult(result, None, transform)
            print("contenttools.doSync(): %s" % (item, ))
            items.append(_syncItem(ctx, session, item))
    select.close()
    if items and all(items):
        update = identifier.Connection.prepareCall('CALL "updateSync"(?, ?, ?)')
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
    id = item.get('id')
    mode = item.get('mode')
    data = None
    print("contenttools._syncItem(): data:\n%s" % (data, ))
    if mode & CREATED:
        data = {'id': id,
                'parents': item.get('parents'),
                'name': item.get('name'),
                'mimeType': item.get('mimeType')}
        print("contenttools._syncItem(): created\n%s" % (data, ))
    if mode & REWRITED:
        size, stream = _getInputStream(ctx, id)
        if size != 0:
            result = uploadItem(ctx, session, id, data, size, stream)
    if mode & RENAMED:
        data = {'name': item.get('name')}
        result = updateItem(session, id, data)
    if mode & TRASHED:
        data = {'trashed': True}
        result = updateItem(session, id, data)
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

def propertyChange(source, name, oldvalue, newvalue):
    if name in source.propertiesListener:
        events = (_getPropertyChangeEvent(source, name, oldvalue, newvalue), )
        for listener in source.propertiesListener[name]:
            listener.propertiesChange(events)

def setContentData(content, call, properties, index=1):
    row = _getContentProperties(content, properties)
    for i, name in enumerate(properties, 1):
        value = row.getObject(i, None)
        print ("items._setContentData(): name:%s - value:%s" % (name, value))
        if value is None:
            continue
        if name in ('Name', 'MimeType'):
            call.setString(index, value)
        elif name in ('DateCreated', 'DateModified'):
            call.setTimestamp(index, value)
        elif name in ('Trashed', 'CanAddChild', 'CanRename', 'IsReadOnly', 'IsVersionable'):
            call.setBoolean(index, value)
        elif name in ('Size', 'Loaded', 'SyncMode'):
            call.setLong(index, value)
        index += 1
    return index

def _getContentProperties(content, properties):
    namedvalues = []
    for name in properties:
        namedvalues.append(getProperty(name))
    command = getCommand('getPropertyValues', tuple(namedvalues))
    return content.execute(command, 0, None)

def setContentProperties(content, arguments):
    properties = []
    for name, value in arguments.items():
        properties.append(getPropertyValue(name, value))
    command = getCommand('setPropertyValues', tuple(properties))
    return content.execute(command, 0, None)

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

def getContentEvent(source, action, content, id):
    event = uno.createUnoStruct('com.sun.star.ucb.ContentEvent')
    event.Source = source
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
    uri = factory.parse(identifier)
    return uri

def getUcb(ctx=None, arguments=None):
    ctx = uno.getComponentContext() if ctx is None else ctx
    arguments = ('Local', 'Office') if arguments is None else arguments
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

def getParametersRequest(source, connection, message):
    r = ParametersRequest()
    r.Message = message
    r.Context = source
    r.Classification = uno.Enum('com.sun.star.task.InteractionClassification', 'QUERY')
    r.Connection = connection
    return r

def getAuthenticationRequest(source, uri, message):
    e = URLAuthenticationRequest()
    e.Message = message
    e.Context = source
    e.Classification = uno.Enum('com.sun.star.task.InteractionClassification', 'QUERY')
    e.ServerName = uri.getScheme()
    e.Diagnostic = message
    e.HasRealm = False
    e.Realm = ''
    e.HasUserName = True
    e.UserName = ''
    e.HasPassword = False
    e.Password = ''
    e.HasAccount = False
    e.Account = ''
    e.URL = uri.getUriReference()
    return e

def getIllegalIdentifierException(source, message):
    e = IllegalIdentifierException()
    e.Message = message
    e.Context = source
    return e

def getInteractiveNetworkOffLineException(source, message):
    e = InteractiveNetworkOffLineException()
    e.Message = message
    e.Context = source
    e.Classification = uno.Enum('com.sun.star.task.InteractionClassification', 'ERROR')
    return e

def getInteractiveNetworkReadException(source, message):
    e = InteractiveNetworkReadException()
    e.Context = source
    e.Message = message
    e.Classification = uno.Enum('com.sun.star.task.InteractionClassification', 'ERROR')
    e.Diagnostic = message
    return e

def getNameClashException(source, message, name):
    e = NameClashException()
    e.Context = source
    e.Message = message
    e.Classification = uno.Enum('com.sun.star.task.InteractionClassification', 'ERROR')
    e.Name = name
    return e

def getUnsupportedNameClashException(source, message):
    e = UnsupportedNameClashException()
    e.Context = source
    e.Message = message
    e.NameClash = uno.getConstantByName('com.sun.star.ucb.NameClash.ERROR')
    return e

def getNameClashResolveRequest(source, message, url, name, newname):
    r = NameClashResolveRequest()
    r.Context = source
    r.Message = message
    r.TargetFolderURL = url
    r.ClashingName = name
    r.ProposedNewName = newname
    r.Classification = uno.Enum('com.sun.star.task.InteractionClassification', 'QUERY')
    return r

def _getInputStream(ctx, id):
    sf = getSimpleFile(ctx)
    url = getResourceLocation(ctx, '%s/%s' % (g_scheme, id))
    if sf.exists(url):
        return sf.getSize(url), sf.openFileRead(url)
    return 0, None
