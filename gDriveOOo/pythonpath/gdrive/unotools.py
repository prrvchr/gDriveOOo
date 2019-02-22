#!
# -*- coding: utf-8 -*-

import uno

from .unolib import InteractionHandler

import binascii


def isCmisReady():
    ctx = uno.getComponentContext()
    product = getOfficeProductName(ctx)
    cmisready = product != 'OpenOffice'
    print("isCmisReady: %s" % cmisready)
    return cmisready

def getOfficeProductName(ctx):
    return getConfiguration(ctx, '/org.openoffice.Setup/Product').getByName('ooName')

def getSimpleFile(ctx):
    return ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')

def getFileSequence(ctx, url, default=None):
    length, sequence = 0, uno.ByteSequence(b'')
    fs = getSimpleFile(ctx)
    if fs.exists(url):
        length, sequence = getSequence(fs.openFileRead(url), fs.getSize(url))
    elif default is not None and fs.exists(default):
        inputstream = fs.openFileRead(default)
        length, sequence = getSequence(fs.openFileRead(default), fs.getSize(default))
    return length, sequence

def getSequence(inputstream, length):
    length, sequence = inputstream.readBytes(None, length)
    inputstream.closeInput()
    return length, sequence

def getProperty(name, type=None, attributes=None, handle=-1):
    property = uno.createUnoStruct('com.sun.star.beans.Property')
    property.Name = name
    property.Handle = handle
    if isinstance(type, uno.Type):
        property.Type = type
    elif type is not None:
        property.Type = uno.getTypeByName(type)
    if attributes is not None:
        property.Attributes = attributes
    return property

def getPropertySetInfoChangeEvent(source, name, reason, handle=-1):
    event = uno.createUnoStruct('com.sun.star.beans.PropertySetInfoChangeEvent')
    event.Source = source
    event.Name = name
    event.Handle = handle
    event.Reason = reason

def getPropertyValueSet(kwargs):
    properties = []
    for key, value in kwargs.items():
        properties.append(getPropertyValue(key, value))
    return tuple(properties)

def getPropertyValue(name, value, state=None, handle=-1):
    property = uno.createUnoStruct('com.sun.star.beans.PropertyValue')
    property.Name = name
    property.Handle = handle
    property.Value = value
    property.State = uno.Enum('com.sun.star.beans.PropertyState', 'DIRECT_VALUE') if state is None else state
    return property

def getNamedValueSet(kwargs):
    namedvalues = []
    for key, value in kwargs.items():
        namedvalues.append(getNamedValue(key, value))
    return tuple(namedvalues)

def getNamedValue(name, value):
    namedvalue = uno.createUnoStruct('com.sun.star.beans.NamedValue')
    namedvalue.Name = name
    namedvalue.Value = value
    return namedvalue

def getResourceLocation(ctx, path='gDriveOOo'):
    identifier = 'com.gmail.prrvchr.extensions.gDriveOOo'
    service = '/singletons/com.sun.star.deployment.PackageInformationProvider'
    provider = ctx.getValueByName(service)
    return '%s/%s' % (provider.getPackageLocation(identifier), path)

def getConfiguration(ctx, nodepath, update=False):
    service = 'com.sun.star.configuration.ConfigurationProvider'
    provider = ctx.ServiceManager.createInstance(service)
    service = 'com.sun.star.configuration.ConfigurationUpdateAccess' if update else \
              'com.sun.star.configuration.ConfigurationAccess'
    namedvalue = uno.createUnoStruct('com.sun.star.beans.NamedValue', "nodepath", nodepath)
    return provider.createInstanceWithArguments(service, (namedvalue, ))

def getCurrentLocale(ctx):
    nodepath = '/org.openoffice.Setup/L10N'
    parts = getConfiguration(ctx, nodepath).getByName('ooLocale').split('-')
    locale = uno.createUnoStruct('com.sun.star.lang.Locale', parts[0], '', '')
    if len(parts) > 1:
        locale.Country = parts[1]
    else:
        service = ctx.ServiceManager.createInstance('com.sun.star.i18n.LocaleData')
        locale.Country = service.getLanguageCountryInfo(locale).Country
    return locale

def getStringResource(ctx, locale=None, filename='DialogStrings'):
    service = 'com.sun.star.resource.StringResourceWithLocation'
    location = getResourceLocation(ctx)
    if locale is None:
        locale = getCurrentLocale(ctx)
    arguments = (location, True, locale, filename, '', InteractionHandler())
    return ctx.ServiceManager.createInstanceWithArgumentsAndContext(service, arguments, ctx)

def generateUuid():
    return binascii.hexlify(uno.generateUuid().value).decode('utf-8')

def createMessageBox(peer, message, title, box='message', buttons=2):
    boxtypes = {'message': 'MESSAGEBOX', 'info': 'INFOBOX', 'warning': 'WARNINGBOX',
                'error': 'ERRORBOX', 'query': 'QUERYBOX'}
    box = uno.Enum('com.sun.star.awt.MessageBoxType', boxtypes[box] if box in boxtypes else 'MESSAGEBOX')
    return peer.getToolkit().createMessageBox(peer, box, buttons, title, message)

def createService(name, ctx=None, **arguments):
    if arguments:
        namedvalues = getNamedValueFromArguments(arguments)
        if ctx:
            service = ctx.ServiceManager.createInstanceWithArgumentsAndContext(name, namedvalues, ctx)
        else:
            service = uno.getComponentContext().ServiceManager.createInstanceWithArguments(name, namedvalues)
    elif ctx:
        service = ctx.ServiceManager.createInstanceWithContext(name, ctx)
    else:
        service = uno.getComponentContext().ServiceManager.createInstance(name)
    return service

def getArgumentsFromNamedValues(namedvalues=()):
    arguments = {}
    for namedvalue in namedvalues:
        arguments[namedvalue.Name] = namedvalue.Value
    return arguments

def getNamedValueFromArguments(arguments={}):
    namedvalues = []
    for key, value in arguments.items():
        namedvalues.append(uno.createUnoStruct('com.sun.star.beans.NamedValue', key, value))
    return tuple(namedvalues)

def getInteractionHandler(ctx, message):
    window = ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop').ActiveFrame.ComponentWindow
    args = (getPropertyValue('Parent', window), getPropertyValue('Context', message))
    interaction = ctx.ServiceManager.createInstanceWithArguments('com.sun.star.task.InteractionHandler', args)
    return interaction
