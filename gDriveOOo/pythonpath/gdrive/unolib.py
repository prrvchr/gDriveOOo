#!
# -*- coding: utf-8 -*-

import uno
import unohelper

from com.sun.star.lang import XComponent, XInitialization
from com.sun.star.beans import XPropertyContainer, XPropertySet, XPropertySetInfo, UnknownPropertyException
from com.sun.star.task import XInteractionHandler
from com.sun.star.ucb import XCommandInfo, UnsupportedCommandException


class Component(XComponent):
    def __init__(self):
        self.listeners = []

    # XComponent
    def dispose(self):
        print("unolib.Component.dispose() 1")
        event = uno.createUnoStruct('com.sun.star.lang.EventObject', self)
        for listener in self.listeners:
            listener.disposing(event)
        print("unolib.Component.dispose() 2 ********************************************************")
    def addEventListener(self, listener):
        print("unolib.Component.addEventListener() *************************************************")
        if listener not in self.listeners:
            self.listeners.append(listener)
    def removeEventListener(self, listener):
        print("unolib.Component.removeEventListener() **********************************************")
        if listener in self.listeners:
            self.listeners.remove(listener)


class Initialization(XInitialization):
    # XInitialization
    def initialize(self, namedvalues=()):
        for namedvalue in namedvalues:
            if hasattr(namedvalue, 'Name') and hasattr(namedvalue, 'Value') and hasattr(self, namedvalue.Name):
                setattr(self, namedvalue.Name, namedvalue.Value)


class InteractionHandler(unohelper.Base, XInteractionHandler):
    # XInteractionHandler
    def handle(self, requester):
        pass


class CommandInfo(unohelper.Base, XCommandInfo):
    def __init__(self, commands={}):
        self.commands = commands

    # XCommandInfo
    def getCommands(self):
        print("PyCommandInfo.getCommands()")
        return tuple(self.commands.values())
    def getCommandInfoByName(self, name):
        print("PyCommandInfo.getCommandInfoByName(): %s" % name)
        if name in self.commands:
            return self.commands[name]
        print("PyCommandInfo.getCommandInfoByName() Error: %s" % name)
        message = 'Cant getCommandInfoByName, UnsupportedCommandException: %s' % name
        raise UnsupportedCommandException(message, self)
    def getCommandInfoByHandle(self, handle):
        print("PyCommandInfo.getCommandInfoByHandle(): %s" % handle)
        for command in self.commands.values():
            if command.Handle == handle:
                return command
        print("PyCommandInfo.getCommandInfoByHandle() Error: %s" % handle)
        message = 'Cant getCommandInfoByHandle, UnsupportedCommandException: %s' % handle
        raise UnsupportedCommandException(message, self)
    def hasCommandByName(self, name):
        print("PyCommandInfo.hasCommandByName(): %s" % name)
        return name in self.commands
    def hasCommandByHandle(self, handle):
        print("PyCommandInfo.hasCommandByHandle(): %s" % handle)
        for command in self.commands.values():
            if command.Handle == handle:
                return True
        return False


class PropertySet(XPropertySet):
    def _getPropertySetInfo(self):
        raise NotImplementedError

    # XPropertySet
    def getPropertySetInfo(self):
        properties = self._getPropertySetInfo()
        return PropertySetInfo(properties)
    def setPropertyValue(self, name, value):
        properties = self._getPropertySetInfo()
        if name in properties and hasattr(self, name):
            setattr(self, name, value)
        else:
            message = 'Cant setPropertyValue, UnknownProperty: %s - %s' % (name, value)
            raise UnknownPropertyException(message, self)
    def getPropertyValue(self, name):
        if name in self._getPropertySetInfo() and hasattr(self, name):
            return getattr(self, name)
        else:
            message = 'Cant getPropertyValue, UnknownProperty: %s' % name
            raise UnknownPropertyException(message, self)
    def addPropertyChangeListener(self, name, listener):
        pass
    def removePropertyChangeListener(self, name, listener):
        pass
    def addVetoableChangeListener(self, name, listener):
        pass
    def removeVetoableChangeListener(self, name, listener):
        pass


class PropertySetInfo(unohelper.Base, XPropertySetInfo):
    def __init__(self, properties):
        self.properties = properties

    # XPropertySetInfo
    def getProperties(self):
        print("PyPropertySetInfo.getProperties()")
        return tuple(self.properties.values())
    def getPropertyByName(self, name):
        print("PyPropertySetInfo.getPropertyByName(): %s" % name)
        if name in self.properties:
            return self.properties[name]
        print("PyPropertySetInfo.getPropertyByName() Error: %s" % name)
        message = 'Cant getPropertyByName, UnknownProperty: %s' % name
        raise UnknownPropertyException(message, self)
    def hasPropertyByName(self, name):
        print("PyPropertySetInfo.hasPropertyByName(): %s" % name)
        return name in self.properties
