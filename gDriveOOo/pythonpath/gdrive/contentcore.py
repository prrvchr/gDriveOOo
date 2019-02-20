#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.uno import Exception as UnoException
from com.sun.star.beans import UnknownPropertyException
from com.sun.star.lang import IllegalArgumentException, IllegalAccessException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
from com.sun.star.ucb.ContentAction import INSERTED, REMOVED, DELETED, EXCHANGED


from .items import insertContentItem, updateName, updateSize, updateTrashed, updateLoaded
from .contenttools import getUri, getContentEvent, getUcp
from .contenttools import getUnsupportedNameClashException, getNameClashException
from .contenttools import getInteractiveIOException, getInteractiveAugmentedIOException
from .contentlib import ContentIdentifier, InteractionRequestName
from .unotools import getInteractionHandler, getNamedValue, getPropertyValueSet
from .children import countChildTitle

import traceback


def getCommandIdentifier(source):
    source.commandIdentifier += 1
    return source.commandIdentifier

def getPropertiesValues(source, properties, logger):
    namedvalues = []
    for property in properties:
        value = None
        msg = "ERROR: Requested property: %s as incorect type" % property
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        if hasattr(property, 'Name') and hasattr(source, property.Name):
            value = getattr(source, property.Name)
            msg = "Get property: %s value: %s" % (property.Name, value)
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        else:
            msg = "ERROR: Requested property: %s is not available" % property.Name
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        logger.logp(level, source.__class__.__name__, "getPropertiesValues()", msg)
        print("%s.getPropertiesValues() %s" % (source.__class__.__name__, msg))
        namedvalues.append(getNamedValue(property.Name, value))
    return tuple(namedvalues)

def setPropertiesValues(source, context, properties, propertyset, logger):
    results = []
    readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
    for position, property in enumerate(properties):
        if hasattr(property, 'Name') and hasattr(property, 'Value'):
            name, value = property.Name, property.Value
            result, level, msg = _setPropertyValue(source, context, propertyset, name, value, position, readonly)
        else:
            msg = "ERROR: Requested property: %s as incorect type" % property
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            error = UnoException(msg, source)
            result = uno.Any('com.sun.star.uno.Exception', error)
        logger.logp(level, source.__class__.__name__, "setPropertiesValues()", msg)
        print("%s.setPropertiesValues() %s" % (source.__class__.__name__, msg))
        results.append(result)
    return tuple(results)

def _setPropertyValue(source, context, propertyset, name, value, position, readonly):
    if name in propertyset:
        if propertyset.get(name).Attributes & readonly:
            msg = "ERROR: Requested property: %s is READONLY" % name
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            error = IllegalAccessException(msg, source)
            result = uno.Any('com.sun.star.lang.IllegalAccessException', error)
        else:
            result, level, msg = _setProperty(source, context, name, value, position)
    else:
        msg = "ERROR: Requested property: %s is not available" % name
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        error = UnknownPropertyException(msg, source)
        result = uno.Any('com.sun.star.beans.UnknownPropertyException', error)
    return result, level, msg

def _setProperty(source, context, name, value, position):
    if name == 'Title':
        result, level, msg = _setTitle(source, context, value, position)
    else:
        setattr(source, name, value)
        msg = "Set property: %s value: %s" % (name, value)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        result = None
    return result, level, msg

def _setTitle(source, context, title, position):
    identifier = source.getIdentifier()
    if u'~' in title:
        print("contentcore._setTitle(): %s - %s" % (title, type(title)))
        msg = "Can't set property: %s value: %s contains invalid character: '~'." % ('Title', title)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        data = getPropertyValueSet({'Uri': identifier.getContentIdentifier(),'ResourceName': title})
        error = getInteractiveAugmentedIOException(msg, context, 'ERROR', 'INVALID_CHARACTER', data)
        result = uno.Any('com.sun.star.ucb.InteractiveAugmentedIOException', error)
    elif countChildTitle(identifier.getParent(), title):
        #msg = "Can't set property: %s value: %s - Name Clash Error" % ('Title', title)
        #level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        #error = IllegalArgumentException(msg, source, position)
        #result = uno.Any('com.sun.star.lang.IllegalArgumentException', error)
        msg = "Can't set property: %s value: %s - Name Clash Error" % ('Title', title)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        data = getPropertyValueSet({'Uri': identifier.getContentIdentifier(),'ResourceName': title})
        error = getInteractiveAugmentedIOException(msg, context, 'ERROR', 'ALREADY_EXISTING', data)
        result = uno.Any('com.sun.star.ucb.InteractiveAugmentedIOException', error)
    else:
        setattr(source, 'Title', title)
        msg = "Set property: %s value: %s" % ('Title', title)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
        result = None
    return result, level, msg

def _getTitle(source, title, position):
    newtitle = _getNewTitle(source, title)
    if title != newtitle:
        #result = {}
        #message = "Name clash!!!"
        #url = '%s/../' % source.getIdentifier().BaseURL
        ##interaction = getInteractionHandler(source.ctx, message)
        #request = InteractionRequestName(source, message, url, title, newtitle, result)
        #if handler.handleInteractionRequest(request):
        #    if result.get('Retrieved', False):
        #        title = result.get('Title')
        #        return _getTitle(source, handler, title, position)
        message = "Title: %s cannot be set. File names must be unique" % title
        e = IllegalArgumentException(message, source, position)
        error = uno.Any('com.sun.star.lang.IllegalArgumentException', e)
        print("contentcore._getTitle() %s" % error)
        return error, title
    return None, title

def _getNewTitle(source, title):
    name, extension = _getTitleExtension(title, '.')
    name, i = _getTitleIndex(name, '~')
    identifier = source.getIdentifier().getParent()
    while True:
        if not countChildTitle(identifier, title):
            break
        i += 1
        title = '%s~%s.%s' % (name, i, extension) if extension else '%s~%s' % (name, i)
    return title

def _getTitleExtension(name, separator):
    basename, extension = name, ''
    names = name.split(separator)
    if len(names) > 1:
        extension = names.pop()
        basename = separator.join(names)
    return basename, extension

def _getTitleIndex(name, separator):
    basename, i = name, 0
    names = name.split(separator)
    if len(names) > 1:
        last = names.pop()
        if last.isdigit():
            i = int(last)
            basename = separator.join(names)
    return basename, i

def updateContent(ctx, event):
    print("contentcore.updateContent() %s - %s" % (event.PropertyName, event.NewValue))
    name, update, result = event.PropertyName, True, False
    identifier = event.Source.getIdentifier()
    if name == 'Id':
        result = insertContentItem(event.Source, identifier, event.NewValue)
    elif name == 'Trashed':
        result = updateTrashed(identifier, event.NewValue)
        #if result:
        #    event.Source.notify(getContentEvent(event.Source, DELETED, event.Source, identifier))
        #action = DELETED
    if name  == 'Name':
        result = updateName(identifier, event.NewValue)
        #if result:
        #    url = '%s/../%s' % (identifier.BaseURL, event.NewValue)
        #    uri = getUri(ctx, url)
        #    id = ContentIdentifier(ctx, identifier.Connection, identifier.Mode, identifier.User, uri)
        #    oldcontent = getUcp(ctx).queryContent(id)
        #    pid = identifier.getParent()
        #    parent = getUcp(ctx).queryContent(pid)
        #    parent.notify(getContentEvent(oldcontent, REMOVED, oldcontent, pid))
        #    parent.notify(getContentEvent(event.Source, INSERTED, event.Source, pid))
            #event.Source.notify(getContentEvent(event.Source, EXCHANGED, event.Source, identifier))
    elif name == 'Size':
        result = updateSize(identifier, event.NewValue)
    elif name == 'Loaded':
        result = updateLoaded(identifier, event.NewValue)
        update = False
    if update and result:
        identifier.update()
        result = identifier.Updated
    print("contentcore.updateContent() %s" % result)
    return result

def notifyContentListener(ctx, source, action, identifier=None):
    if action == INSERTED:
        identifier = source.getIdentifier().getParent()
        parent = getUcp(ctx).queryContent(identifier)
        parent.notify(getContentEvent(action, source, identifier))
    elif action == DELETED:
        identifier = source.getIdentifier()
        source.notify(getContentEvent(action, source, identifier))
    elif action == EXCHANGED:
        source.notify(getContentEvent(action, source, identifier))

