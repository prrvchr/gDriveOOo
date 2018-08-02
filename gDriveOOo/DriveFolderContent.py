#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo, NoSupportException
from com.sun.star.awt import XCallback
from com.sun.star.ucb import XContent, XCommandProcessor2, XContentCreator, IllegalIdentifierException
from com.sun.star.container import XChild
from com.sun.star.beans import UnknownPropertyException
from com.sun.star.uno import Exception

from gdrive import Component, Initialization, CommandInfo, PropertySetInfo, Row, DynamicResultSet, PropertiesChangeNotifier
from gdrive import getItemUpdate
from gdrive import getPropertyChangeEvent

from gdrive import updateItem, updateChildren, createService, getSimpleFile, getResourceLocation
from gdrive import getUcb, getCommandInfo, getProperty, getContentInfo
from gdrive import queryContentIdentifier, queryContent
from gdrive import getIdSelectStatement, getNewId, insertItem, getContentEvent

import requests
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'


class DriveFolderContent(unohelper.Base, XServiceInfo, Component, Initialization, PropertiesChangeNotifier,
                         XContent, XCommandProcessor2, XContentCreator, XChild, XCallback):
    def __init__(self, ctx, *namedvalues):
        try:
            self.ctx = ctx
            self.Scheme = None
            self.UserName = None
            self.Id = None
            self.ParentId = None

            self.ContentType = 'application/vnd.google-apps.folder'
            self.IsFolder = True
            self.IsDocument = False
            self._Title = 'Sans Nom'
            
            self.MediaType = None
            self.Size = 0
            self.DateModified = None
            self.DateCreated = None
            self._IsInCache = False
            
            self.listeners = []
            self.contentListeners = []
            #PropertiesChangeNotifier listeners
            self.propertiesListener = {}
            #XPropertySetInfoChangeNotifier listeners
            self.propertyInfoListeners = []
            #XCommandInfoChangeNotifier listeners
            self.commandInfoListeners = []
            
            self.initialize(namedvalues)

            print("DriveFolderContent.__init__()")
        except Exception as e:
            print("DriveFolderContent.__init__().Error: %s - %e" % (e, traceback.print_exc()))

    @property
    def IsInCache(self):
        return self._IsInCache
    @IsInCache.setter
    def IsInCache(self, state):
        if 'IsInCache' in self.propertiesListener:
            events = (getPropertyChangeEvent(self, 'IsInCache', self._IsInCache, state), )
            for listener in self.propertiesListener['IsInCache']:
                listener.propertiesChange(events)
        self._IsInCache = state
    @property
    def Title(self):
        return self._Title
    @Title.setter
    def Title(self, title):
        if 'Title' in self.propertiesListener:
            events = (getPropertyChangeEvent(self, 'Title', self._Title, title), )
            for listener in self.propertiesListener['Title']:
                listener.propertiesChange(events)
        self._Title = title

    # XCallback
    def notify(self, data):
        for listener in self.contentListeners:
            listener.contentEvent(data)

    # XContentCreator
    def queryCreatableContentsInfo(self):
        print("DriveFolderContent.queryCreatableContentsInfo():*************************")
        return self._getCreatableContentsInfo()
    def createNewContent(self, contentinfo):
        print("DriveFolderContent.createNewContent():************************* %s" % contentinfo)
        pass

    # XChild
    def getParent(self):
        print("DriveFolderContent.getParent()")
        identifier = '%s://%s/%s' % (self.Scheme, self.UserName, self.Id)
        return queryContent(self.ctx, identifier)
    def setParent(self, parent):
        raise NoSupportException('Parent can not be set', self)

    # XContent
    def getIdentifier(self):
        identifier = '%s://%s/%s' % (self.Scheme, self.UserName, self.Id)
        return queryContentIdentifier(self.ctx, identifier)
    def getContentType(self):
        return 'application/vnd.google-apps.folder'
    def addContentEventListener(self, listener):
        #print("DriveFolderContent.addContentEventListener():*************************")
        self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        #print("DriveFolderContent.removeContentEventListener():*************************")
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)

    # XCommandProcessor2
    def createCommandIdentifier(self):
        return 0
    def execute(self, command, id, environment):
        try:
            print("DriveFolderContent.execute(): %s" % command.Name)
            if command.Name == 'getCommandInfo':
                return CommandInfo(self._getCommandInfo())
            elif command.Name == 'getPropertySetInfo':
                return PropertySetInfo(self._getPropertySetInfo())
            elif command.Name == 'getPropertyValues':
                values = self._getPropertyValues(command.Argument)
                return Row(values)
            elif command.Name == 'setPropertyValues':
                results = []
                for property in command.Argument:
                    result = Exception('SetProperty Exception', self)
                    if hasattr(property, 'Name') and hasattr(property, 'Value'):
                        if hasattr(self, property.Name):
                            setattr(self, property.Name, property.Value)
                            result = None
                        else:
                            result = UnknownPropertyException('UnknownProperty: %s' % property.Name, self)
                    results.append(result)
                print("DriveFolderContent.execute() setPropertyValues: %s" % (arguments, ))
                return tuple(results)
            elif command.Name == 'open':
                if not self.IsInCache:
                    updateChildren(self.ctx, self.Scheme, self.UserName, self.Id)
                    self.IsInCache = True
                return DynamicResultSet(self.ctx, self.Scheme, self.UserName, self.Id, command.Argument)
            elif command.Name == 'createNewContent':
                if command.Argument.Type == 'application/vnd.google-apps.folder':
                    print("DriveFolderContent.execute(): createNewContent %s" % command.Argument)
                    id = getNewId(self.authentication, self.IdSelect, self.UserName)
                    kwargs = {'Scheme': self.Scheme, 'UserName': self.UserName, 'Id': id, 'ParentId': self.Id, 'NewItem': True}
                    name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'
                    content = createService(name, self.ctx, **kwargs)
                    return content
            elif command.Name == 'insert':
                print("DriveFolderContent.execute() insert")
                #arguments = self._getNewValues()
                #insertItem(self.ItemInsert, arguments)
                #insertParent(self.ItemInsert.getConnection(), arguments)
                #identifier = queryContentIdentifier(self.ctx, self.Scheme, self.UserName, self.ParentId)
                #action = uno.getConstantByName('com.sun.star.ucb.ContentAction.INSERTED')
                #event = getContentEvent(action, self, identifier)
                #parent = queryContent(self.ctx, self.Scheme, self.UserName, self.ParentId)
                #parent.notify(event)
            elif command.Name == 'delete':
                print("DriveFolderContent.execute(): delete")
            elif command.Name == 'transfer':
                source = command.Argument.SourceURL
                sf = getSimpleFile(self.ctx)
                if sf.exists(source):
                    id = command.Argument.NewTitle
                    target = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, id))
                    inputstream = sf.openFileRead(source)
                    sf.writeFile(target, inputstream)
                    inputstream.closeInput()
                    #size = sf.getSize(target)
                    if command.Argument.MoveData:
                        pass #must delete object
            elif command.Name == 'close':
                print("DriveFolderContent.execute(): close")
        except Exception as e:
            print("DriveFolderContent.execute().Error: %s - %e" % (e, traceback.print_exc()))

    def abort(self, id):
        pass
    def releaseCommandIdentifier(self, id):
        pass

    def _getPropertyValues(self, properties):
        values = []
        for property in properties:
            value = None
            if hasattr(property, 'Name') and hasattr(self, property.Name):
                value = getattr(self, property.Name)
            else:
                print("DriveFolderContent._getPropertyValues().Error: %s " % (property.Name, ))
            values.append(uno.createUnoStruct('com.sun.star.beans.NamedValue', property.Name, value))
        return tuple(values)

    def _getCommandInfo(self):
        commands = {}
        commands['getCommandInfo'] = getCommandInfo('getCommandInfo')
        commands['getPropertySetInfo'] = getCommandInfo('getPropertySetInfo')
        commands['getPropertyValues'] = getCommandInfo('getPropertyValues', '[]com.sun.star.beans.Property')
        commands['setPropertyValues'] = getCommandInfo('setPropertyValues', '[]com.sun.star.beans.PropertyValue')
        commands['open'] = getCommandInfo('open', 'com.sun.star.ucb.OpenCommandArgument2')
        commands['createNewContent'] = getCommandInfo('createNewContent', 'com.sun.star.ucb.ContentInfo')
        commands['insert'] = getCommandInfo('insert', 'com.sun.star.ucb.InsertCommandArgument')
        commands['delete'] = getCommandInfo('delete', 'boolean')
        commands['transfer'] = getCommandInfo('transfer', 'com.sun.star.ucb.TransferInfo')
        commands['close'] = getCommandInfo('close')
        return commands

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['Id'] = getProperty('Id', 'string', readonly)
#        properties['ParentsId'] = getProperty('ParentsId', '[]string', readonly)
        properties['ContentType'] = getProperty('ContentType', 'string', readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', readonly)
        properties['Title'] = getProperty('Title', 'string', transient)
        properties['Size'] = getProperty('Size', 'long', readonly)
        properties['DateModified'] = getProperty('DateModified', 'com.sun.star.util.DateTime', readonly)
        properties['DateCreated'] = getProperty('DateCreated', 'com.sun.star.util.DateTime', readonly)
#        properties['CreatableContentsInfo'] = getProperty('CreatableContentsInfo', '[]com.sun.star.ucb.ContentInfo', readonly)
        return properties

    def _getCreatableContentsInfo(self):
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        document = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_DOCUMENT')
        folder = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_FOLDER')
        ctype = 'application/vnd.google-apps.folder'
        properties = (getProperty('Title', 'string', transient), )
        content = (getContentInfo(ctype, folder, properties), )
        return content

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(DriveFolderContent,                        # UNO object class
                                         g_ImplementationName,                      # Implementation name
                                        (g_ImplementationName,))                    # List of implemented services
