#!
# -*- coding: utf-8 -*-

import uno
from com.sun.star.beans import UnknownPropertyException, IllegalTypeException

import datetime
import requests
import traceback


def getPropertyChangeEvent(source, name, oldvalue, newvalue, further=False, handle=-1):
    event = uno.createUnoStruct('com.sun.star.beans.PropertyChangeEvent')
    event.Source = source
    event.PropertyName = name
    event.Further = further
    event.PropertyHandle = handle
    event.OldValue = oldvalue
    event.NewValue = newvalue
    print("contenttools.getPropertyChangeEvent")
    return event
    
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

def queryContentIdentifier(ctx, identifier):
    return getUcb(ctx).createContentIdentifier(identifier)

def queryContent(ctx, identifier):
    ucb = getUcb(ctx)
    return ucb.queryContent(ucb.createContentIdentifier(identifier))

def getCmisProperty(id, name, value, typename, updatable=True, required=True, multivalued=False, openchoice=True, choices=None):
    property = uno.createUnoStruct('com.sun.star.document.CmisProperty')
    property.Id = id
    property.Name = name
    property.Type = typename
    property.Updatable = updatable
    property.Required= required
    property.MultiValued = multivalued
    property.OpenChoice = openchoice
    if choices is not None:
        property.Choices = choices
    property.Value = value
    return property

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

def getPropertiesValues(self, properties):
    values = []
    for property in properties:
        value = None
        if hasattr(property, 'Name'):
            if property.Name == 'CasePreservingURL':
                id = createIdentifier(self.auth, self.url, self.Title)
                value = queryContentIdentifierString(self.Scheme, self.UserName, id)
            elif hasattr(self, property.Name):
                value = getattr(self, property.Name)
        values.append(value)
        print("contenttools.getPropertiesValues(): %s - %s" % (property.Name, value))
    return tuple(values)

def setPropertiesValues(self, properties):
    result = []
    for property in properties:
        if hasattr(property, 'Name') and hasattr(property, 'Value'):
            if hasattr(self, property.Name):
                setattr(self, property.Name, property.Value)
                result.append(None)
                print("contenttools.setPropertiesValues(): %s - %s" % (property.Name, property.Value))
            else:
                result.append(UnknownPropertyException)
        else:
            result.append(IllegalTypeException)
    return tuple(result)

def getArgumentColumns(argument):
    columns = []
    for property in argument.Properties:
        if hasattr(property, 'Name'):
            columns.append(property.Name)
    return columns

def getContentValues(content, properties):
    arguments = []
    for property in properties:
        arguments.append(getProperty(property))
    command = uno.createUnoStruct('com.sun.star.ucb.Command', 'getPropertyValues', -1, tuple(arguments))
    rows = content.execute(command, 0, None)
    return _getResultFromRows(rows, properties)

def _getResultFromRows(rows, properties):
    i = 1
    result = {}
    for property in properties.values():
        value = rows.getObject(i, None)
        if property == 'modifiedTime':
            value = unparseDateTime(value)
        elif property == 'parents':
            value = list(value)
        result[property] = value
        i += 1
    return result

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

