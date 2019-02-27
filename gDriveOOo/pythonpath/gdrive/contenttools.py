#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.ucb import NameClashResolveRequest
from com.sun.star.ucb import IllegalIdentifierException
from com.sun.star.ucb import InteractiveNetworkOffLineException
from com.sun.star.ucb import InteractiveNetworkReadException
from com.sun.star.ucb import UnsupportedNameClashException
from com.sun.star.ucb import NameClashException
from com.sun.star.ucb import URLAuthenticationRequest
from com.sun.star.ucb import InteractiveIOException
from com.sun.star.ucb import InteractiveAugmentedIOException
from com.sun.star.sdb import ParametersRequest

from .dbtools import getItemFromResult
from .google import OAuth2Ooo
from .google import OutputStream
from .google import g_doc_map
from .google import g_folder
from .google import g_link
from .google import getUploadLocation
from .google import updateItem
from .google import RETRIEVED
from .google import CREATED
from .google import FOLDER
from .google import FILE
from .google import RENAMED
from .google import REWRITED
from .google import TRASHED
from .unotools import getProperty
from .unotools import getPropertyValue
from .unotools import getSimpleFile
from .unotools import getResourceLocation
from .unotools import getNamedValueSet

import requests

g_OfficeDocument = 'application/vnd.oasis.opendocument'


def createContentUser(ctx, plugin, scheme, connection, username=None):
    service = '%s.ContentUser' % plugin
    namedvalue = getNamedValueSet({'Scheme': scheme, 'Connection': connection, 'Name': username})
    contentuser = ctx.ServiceManager.createInstanceWithArgumentsAndContext(service, namedvalue, ctx)
    return contentuser

def createContentIdentifier(ctx, plugin, user, uri):
    service = '%s.ContentIdentifier' % plugin
    namedvalue = getNamedValueSet({'User': user, 'Uri': uri})
    contentidentifier = ctx.ServiceManager.createInstanceWithArgumentsAndContext(service, namedvalue, ctx)
    return contentidentifier

def createContent(ctx, mimetype, identifier, data={}):
    name, content = None, None
    if mimetype == g_folder:
        name = 'DriveFolderContent'
    elif mimetype == g_link:
        pass
    elif mimetype in (g_doc_map):
        name = 'DriveDocumentContent'
    elif mimetype.startswith(g_OfficeDocument):
        name = 'DriveOfficeContent'
    if name is not None:
        service = 'com.gmail.prrvchr.extensions.gDriveOOo.%s' % name
        namedvalue = getNamedValueSet({'Identifier': identifier})
        namedvalue += getNamedValueSet(data)
        content = ctx.ServiceManager.createInstanceWithArgumentsAndContext(service, namedvalue, ctx)
    return content

def getSession(ctx, scheme, username):
    session = requests.Session()
    session.auth = OAuth2Ooo(ctx, scheme, username)
    return session

def doSync(ctx, scheme, connection, session, userid):
    items = []
    #data = ('name', 'createdTime', 'modifiedTime', 'mimeType')
    transform = {'parents': lambda value: value.split(',')}
    select = connection.prepareCall('CALL "selectSync"(?, ?)')
    select.setString(1, userid)
    select.setLong(2, RETRIEVED)
    result = select.executeQuery()
    while result.next():
        item = getItemFromResult(result, None, transform)
        print("contenttools.doSync(): %s" % (item, ))
        items.append(_syncItem(ctx, scheme, session, item))
    select.close()
    if items and all(items):
        update = connection.prepareCall('CALL "updateSync"(?, ?, ?, ?)')
        update.setString(1, userid)
        update.setString(2, ','.join(items))
        update.setLong(3, RETRIEVED)
        update.execute()
        r = update.getLong(4)
        print("contenttools.doSync(): all -> Ok %s" % r)
    else:
        print("contenttools.doSync(): all -> Error")
    print("doSync: %s" % items)
    return all(items)

def _syncItem(ctx, scheme, session, item):
    result = False
    id = item.get('id')
    mode = item.get('mode')
    data = None 
    print("contenttools._syncItem():\nmode: %s\ndata: %s" % (mode, data))
    if mode & CREATED:
        data = {'id': id,
                'parents': item.get('parents'),
                'name': item.get('name'),
                'mimeType': item.get('mimeType')}
        print("contenttools._syncItem(): created\n%s" % (data, ))
        if mode & FOLDER:
            result = updateItem(session, id, data, True)
        if mode & FILE:
            mimetype = item.get('mimeType')
            result = uploadItem(ctx, scheme, session, id, data, mimetype, True)
    else:
        if mode & REWRITED:
            mimetype = None if item.get('size') else item.get('mimeType')
            result = uploadItem(ctx, scheme, session, id, data, mimetype, False)
        if mode & RENAMED:
            data = {'name': item.get('name')}
            result = updateItem(session, id, data, False)
    if mode & TRASHED:
        data = {'trashed': True}
        result = updateItem(session, id, data, False)
    return result

def uploadItem(ctx, scheme, session, id, data, mimetype, new):
    size, stream = _getInputStream(ctx, scheme, id)
    if size: 
        location = getUploadLocation(session, id, data, mimetype, new, size)
        if location is not None:
            mimetype = None
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
        elif name in ('Size', 'Loaded'):
            call.setLong(index, value)
        index += 1
    return index

def _getContentProperties(content, properties):
    namedvalues = []
    for name in properties:
        namedvalues.append(getProperty(name))
    command = getCommand('getPropertyValues', tuple(namedvalues))
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

def getContentInfo(ctype, attributes=0, properties=()):
    info = uno.createUnoStruct('com.sun.star.ucb.ContentInfo')
    info.Type = ctype
    info.Attributes = attributes
    info.Properties = properties
    return info

def getInsertCommandArgument(data, replace):
    insert = uno.createUnoStruct('com.sun.star.ucb.InsertCommandArgument')
    insert.Data = data
    insert.ReplaceExisting = replace
    return insert

def getUri(ctx, identifier):
    factory = ctx.ServiceManager.createInstance('com.sun.star.uri.UriReferenceFactory')
    uri = factory.parse(identifier)
    return uri

def getUcb(ctx=None, arguments=None):
    ctx = uno.getComponentContext() if ctx is None else ctx
    arguments = ('Local', 'Office') if arguments is None else arguments
    name = 'com.sun.star.ucb.UniversalContentBroker'
    return ctx.ServiceManager.createInstanceWithArguments(name, (arguments, ))

def getUcp(ctx, scheme):
    return getUcb(ctx).queryContentProvider('%s://' % scheme)

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

def getInteractiveAugmentedIOException(message, source, Classification, code, arguments):
    e = InteractiveAugmentedIOException()
    e.Message = message
    e.Context = source
    e.Classification = uno.Enum('com.sun.star.task.InteractionClassification', Classification)
    e.Code = uno.Enum('com.sun.star.ucb.IOErrorCode', code)
    e.Arguments = arguments
    return e

def getInteractiveIOException(message, source, Classification, code):
    e = InteractiveIOException()
    e.Message = message
    e.Context = source
    e.Classification = uno.Enum('com.sun.star.task.InteractionClassification', Classification)
    e.Code = uno.Enum('com.sun.star.ucb.IOErrorCode', code)
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

def _getInputStream(ctx, scheme, id):
    sf = getSimpleFile(ctx)
    url = getResourceLocation(ctx, '%s/%s' % (scheme, id))
    if sf.exists(url):
        return sf.getSize(url), sf.openFileRead(url)
    return 0, None
