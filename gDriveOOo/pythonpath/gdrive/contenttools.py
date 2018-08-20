#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.beans import UnknownPropertyException, IllegalTypeException
from com.sun.star.uno import Exception as UnoException

from .unotools import getProperty, getPropertyValue
from .items import insertItem, updateItem
from .children import insertParent
from .identifiers import updateIdentifier

import datetime
import requests
import traceback


def insertContent(ctx, event, itemInsert, childInsert, idUpdate, root):
    properties = ('Uri', 'Title', 'DateCreated', 'DateModified', 'MediaType', 'IsVersionable')
    row = getContentProperties(event.Source, properties)
    uri = row.getObject(1, None)
    parent = getId(getParentUri(ctx, uri), root)
    return all((insertItem(itemInsert, event.NewValue, row),
                insertParent(childInsert, event.NewValue, parent),
                updateIdentifier(idUpdate, event.NewValue)))

def updateContent(event, statement):
    id = getContentProperties(event.Source, ('Id', )).getString(1)
    return updateItem(event, statement, id)

def propertyChange(source, name, oldvalue, newvalue):
    #mri = source.ctx.ServiceManager.createInstance('mytools.Mri')
    if name in source.propertiesListener:
        events = (_getPropertyChangeEvent(source, name, oldvalue, newvalue), )
        for listener in source.propertiesListener[name]:
            #mri.inspect(listener)
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
        id = uri.getPathSegment(count -1)
    if count == 1 and id == "":
        id = root
    return id

def getNewItem(ctx, uri, username):
    paths = getUriPath(uri, 'new')
    id = '%s://%s/%s' % (uri.getScheme(), uri.getAuthority(), '/'.join(paths))
    identifier = getUcp(ctx, id).createContentIdentifier(id)
    id = getId(getUri(ctx, identifier.getContentIdentifier()))
    uri = getUri(ctx, identifier.getContentIdentifier())
    return {'UserName': username, 'Id': id, 'Uri': uri}

def getUriPath(uri, path=None, remove=False):
    paths = []
    for index in range(uri.getPathSegmentCount()):
        paths.append(uri.getPathSegment(index))
    if remove and len(paths):
        paths.pop()
    if path is not None:
        paths.append(path)
    return paths

def getParentUri(ctx, uri):
    path = getUriPath(uri, None, True)
    identifier = '%s://%s/%s' % (uri.getScheme(), uri.getAuthority(), '/'.join(path))
    return getUri(ctx, identifier)

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

def getSimpleFile(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')

def getTempFile(ctx):
    tmp = ctx.ServiceManager.createInstance('com.sun.star.io.TempFile')
    tmp.RemoveFile = False
    return tmp

def getPump(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.io.Pump')

def getPipe(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.io.Pipe')

def getResultSet(auth, url, id, fields):
    rows = []
    final = True
    timeout = 10
    params = {}
    params['q'] = "'%s' in parents" % id
    params['fields'] = fields
    try:
        with requests.get(url, params=params, timeout=timeout, auth=auth) as r:
            print("contenttools.getResultSet(): %s" % r.json())
            if r.status_code == requests.codes.ok:
                result = r.json()
                if 'files' in result:
                    rows = result['files']
                if 'incompleteSearch' in result:
                    final = not bool(result['incompleteSearch'])
        return (rows, final)
    except Exception as e:
        print("contenttools.getResultSet() ERROR: %s" % e)

def getResultContent(auth, url, fields, token=None, pages=100):
    rows = []
    final = True
    timeout = 10
    params = {}
    params['fields'] = fields
    params['pageSize'] = pages
    if token is not None:
        params['pageToken'] = token
    token = None
    try:
        with requests.get(url, params=params, timeout=timeout, auth=auth) as r:
            print("contenttools.getResultContent(): %s" % r.json())
            if r.status_code == requests.codes.ok:
                result = r.json()
                if 'files' in result:
                    rows = result['files']
                if 'nextPageToken' in result:
                    token = result['nextPageToken']
        return (rows, token)
    except Exception as e:
        print("contenttools.getResultContent() ERROR: %s" % e)

def getNewIdentifier(auth, url):
    ids = []
    url += '/generateIds'
    timeout = 10
    params = {'space': 'drive'}
    with requests.get(url, params=params, timeout=timeout, auth=auth) as r:
        if r.status_code == requests.codes.ok:
            result = r.json()
            if 'ids' in result:
                ids = result['ids']
                print("contenttools.getNewIdentifier(): %s" % (ids, ))
    return ids

def createIdentifier(auth, url, title):
    id = None
    timeout = 10
    data = {'name': title}
#    data['mimeType'] = mimetype
#    data['parents'] = list(parents)
    with requests.post(url, json=data, timeout=timeout, auth=auth) as r:
        if r.status_code == requests.codes.ok:
            result = r.json()
            if 'id' in result:
                id = result['id']
                print("contenttools.createIdentifier(): %s" % id)
    return id

def getContent(ctx, identifier):
    return getUcb(ctx).queryContent(identifier)

def getContentEvent(action, content, id):
    event = uno.createUnoStruct('com.sun.star.ucb.ContentEvent')
    event.Action = action
    event.Content = content
    event.Id = id
    return event

def parseDateTime(timestr=None, format=u'%Y-%m-%dT%H:%M:%S.%fZ'):
    if timestr is None:
        t = datetime.datetime.now()
    else:
        t = datetime.datetime.strptime(timestr, format)
    return getDateTime(t.microsecond, t.second, t.minute, t.hour, t.day, t.month, t.year)

def unparseDateTime(t):
    if hasattr(t, 'HundredthSeconds'):
        timestr = '%s-%s-%sT%s:%s:%s.%sZ' % (t.Year, t.Month, t.Day, t.Hours, t.Minutes, t.Seconds, t.HundredthSeconds * 10)
    elif hasattr(t, 'NanoSeconds'):
        timestr = '%s-%s-%sT%s:%s:%s.%sZ' % (t.Year, t.Month, t.Day, t.Hours, t.Minutes, t.Seconds, t.NanoSeconds // 1000000)
    return timestr

def getDateTime(microsecond=0, second=0, minute=0, hour=0, day=1, month=1, year=1970, utc=True):
    t = uno.createUnoStruct('com.sun.star.util.DateTime')
    t.Year = year
    t.Month = month
    t.Day = day
    t.Hours = hour
    t.Minutes = minute
    t.Seconds = second
    if hasattr(t, 'HundredthSeconds'):
        t.HundredthSeconds = microsecond // 10000
    elif hasattr(t, 'NanoSeconds'):
        t.NanoSeconds = microsecond * 1000
    if hasattr(t, 'IsUTC'):
        t.IsUTC = utc
    return t

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

def getUploadLocation(auth, id, name, parent, size, mimetype):
    location = None
    url = 'https://www.googleapis.com/upload/drive/v3/files/%s' % id
    print("contenttools.getUploadLocation()1: %s - %s" % (id, size))
    session = requests.Session()
    headers = {}
    headers['X-Upload-Content-Length'] = '%s' % size
    headers['X-Upload-Content-Type'] = mimetype
    headers['Content-Type'] = 'application/json; charset=UTF-8'
    params = {'uploadType': 'resumable'}
    json = {'name': name, 'parentsId': [parent]}
    with session.patch(url, headers=headers, params=params, json=json, auth=auth) as r:
        print("contenttools.getUploadLocation()2 %s - %s" % (r.status_code, r.headers))
        if r.status_code == requests.codes.ok:
            if 'Location' in r.headers:
                location = r.headers['Location']
    return location

