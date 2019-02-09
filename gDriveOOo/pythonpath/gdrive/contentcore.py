#!
# -*- coding: utf-8 -*-

import uno

from com.sun.star.uno import Exception as UnoException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE
from com.sun.star.ucb.ContentAction import INSERTED, REMOVED, DELETED, EXCHANGED


from .items import insertContentItem, updateName, updateSize, updateTrashed, updateLoaded
from .contenttools import doSync, getUri, getContentEvent, getUcp
from .contenttools import getUnsupportedNameClashException
from .contentlib import ContentIdentifier, InteractionRequestName
from .unotools import getInteractionHandler, getNamedValue
from .children import countChildTitle

import traceback


def getPropertiesValues(source, properties, logger):
    namedvalues = []
    for property in properties:
        value = None
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        msg = "ERROR: Requested property: %s as incorect type" % property
        if hasattr(property, 'Name') and hasattr(source, property.Name):
            value = getattr(source, property.Name)
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
            msg = "Get property: %s value: %s" % (property.Name, value)
        else:
            level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
            msg = "ERROR: Requested property: %s is not available" % property.Name
        logger.logp(level, source.__class__.__name__, "getPropertiesValues()", msg)
        print("%s.getPropertiesValues() %s" % (source.__class__.__name__, msg))
        namedvalues.append(getNamedValue(property.Name, value))
    return tuple(namedvalues)

def setPropertiesValues(source, properties, logger):
    results = []
    for property in properties:
        result = UnoException('SetProperty Exception', source)
        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
        msg = "ERROR: Requested property: %s as incorect type" % property
        if hasattr(property, 'Name') and hasattr(property, 'Value'):
            if hasattr(source, property.Name):
                level = uno.getConstantByName('com.sun.star.logging.LogLevel.INFO')
                msg = "Set property: %s value: %s" % (property.Name, property.Value)
                if property.Name == 'Title':
                    value, result = _getUniqueTitle(source, property.Value)
                    if result is None:
                        if property.Value != value:
                            notifyContentListener(source.ctx, source, DELETED)
                            setattr(source, property.Name, value)
                            notifyContentListener(source.ctx, source, INSERTED)
                        else:
                            setattr(source, property.Name, value)
                    else:
                        notifyContentListener(source.ctx, source, DELETED)
                        notifyContentListener(source.ctx, source, INSERTED)
                        level = uno.getConstantByName('com.sun.star.logging.LogLevel.SEVERE')
                        msg = "Can't set property: %s value: %s - NameClash ERROR" % (property.Name, value)
                else:
                    setattr(source, property.Name, property.Value)
                    result = None
            else:
                result = UnknownPropertyException('UnknownProperty: %s' % property.Name, source)
                msg = "ERROR: Requested property: %s is not available" % property.Name
        logger.logp(level, source.__class__.__name__, "setPropertiesValues()", msg)
        print("%s.setPropertiesValues() %s" % (source.__class__.__name__, msg))
        results.append(result)
    return tuple(results)
        
def _getUniqueTitle(source, title):
    name, extention = title, ''
    namelist = title.split('.')
    if len(namelist) > 1:
        extension = namelist.pop()
        name = '.'.join(namelist)
    i, count, newtitle = 0, 1, title
    identifier = source.getIdentifier().getParent()
    while count != 0:
        count = countChildTitle(identifier, newtitle)
        newtitle = '%s~%s.%s' % (name, i, extension)
        i += 1
    if i != 1:
        result = {}
        message = "Name clash!!!"
        url = source.getIdentifier().getContentIdentifier()
        interaction = getInteractionHandler(source.ctx, message)
        request = InteractionRequestName(source, message, url, title, newtitle, result)
        if interaction.handleInteractionRequest(request):
            if result.get('Retrieved', False):
                title = result.get('Title')
                return _getUniqueTitle(source, title)
        message = "Title: %s cannot be set. File names must be unique" % title
        e = getUnsupportedNameClashException(source, message)
        return title, e
    return title, None

def updateContent(ctx, event, mode):
    print("contentcore.updateContent() %s - %s" % (event.PropertyName, event.NewValue))
    result, action, sync = False, None, True
    identifier = event.Source.getIdentifier()
    if event.PropertyName == 'Id':
        result = insertContentItem(event.Source, identifier, event.NewValue)
        action = INSERTED
    elif event.PropertyName == 'Trashed':
        result = updateTrashed(identifier, event.NewValue)
        action = DELETED
    if result:
        notifyContentListener(ctx, event.Source, action)
    if event.PropertyName  == 'Name':
        result = updateName(identifier, event.NewValue)
        #action = EXCHANGED
    elif event.PropertyName == 'Size':
        result = updateSize(identifier, event.NewValue)
    elif event.PropertyName == 'Loaded':
        result = updateLoaded(identifier, event.NewValue)
        sync = False
    if sync and result and mode == ONLINE:
        result = doSync(ctx, identifier)
    print("contentcore.updateContent() %s" % result)
    return result

def notifyContentListener(ctx, source, action):
    if action == INSERTED:
        identifier = source.getIdentifier().getParent()
        parent = getUcp(ctx).queryContent(identifier)
        parent.notify(getContentEvent(action, source, identifier))
    elif action == DELETED:
        source.notify(getContentEvent(action, source, source.getIdentifier()))
    #elif action == EXCHANGED:
    #    source.notify(getContentEvent(action, source, event.OldValue))

