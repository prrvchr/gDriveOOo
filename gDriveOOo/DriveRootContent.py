#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.awt import XCallback
from com.sun.star.ucb import XContent, XCommandProcessor2, XContentCreator, IllegalIdentifierException
from com.sun.star.beans import UnknownPropertyException
from com.sun.star.uno import Exception

from gdrive import Component, Initialization, CommandInfo, PropertySetInfo, Row, DynamicResultSet, PropertiesChangeNotifier
from gdrive import getItemUpdate
from gdrive import updateItem, updateChildren, createService, getSimpleFile, getResourceLocation
from gdrive import getUcb, queryContentIdentifier, getCommandInfo, getProperty, getContentInfo
from gdrive import getIdSelectStatement, getNewId
from gdrive import getPropertyChangeEvent

#from gdrive import PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier, PyPropertyContainer, PyDynamicResultSet
import requests
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveRootContent'


class DriveRootContent(unohelper.Base, XServiceInfo, Component, Initialization, PropertiesChangeNotifier,
                       XContent, XCommandProcessor2, XContentCreator, XCallback):
    def __init__(self, ctx, *namedvalues):
        try:
            self.ctx = ctx
            self.Scheme = None
            self.UserName = None
            self.Id = None
            self.refCounter = 0
            
            self.ContentType = 'application/vnd.google-apps.folder-root'
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
            #PyPropertiesChangeNotifier listeners
            self.propertiesListener = {}
            #XPropertySetInfoChangeNotifier listeners
            self.propertyInfoListeners = []
            #XCommandInfoChangeNotifier listeners
            self.commandInfoListeners = []
#            self.commands = self._getCommandInfo()
            
            self.initialize(namedvalues)

            #url = getResourceLocation(self.ctx, '%s.odb' % self.Scheme)
            #db = self.ctx.ServiceManager.createInstance("com.sun.star.sdb.DatabaseContext").getByName(url)
            #connection = db.getConnection('', '')
            #query = uno.getConstantByName('com.sun.star.sdb.CommandType.QUERY')
            #self.ItemSelect = connection.prepareCommand('getItem', query)
            #self.itemSelect.setString(1, self.UserName)
            #self.ItemUpdate = getItemUpdate(connection, self.Id)
            #self.IdSelect = getIdSelectStatement(connection, self.UserName)
            
            print("DriveRootContent.__init__()")
        except Exception as e:
            print("DriveRootContent.__init__().Error: %s - %s" % (e, traceback.print_exc()))

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

    # XInterface
    def acquire(self):
        self.refCounter += 1
        print("DriveRootContent.acquire() %s" % self.refCounter)
    def release(self):
        self.refCounter -= 1
        print("DriveRootContent.release() %s" % self.refCounter)

    # XCallback
    def notify(self, data):
        for listener in self.contentListeners:
            listener.contentEvent(data)

    # XContentCreator
    def queryCreatableContentsInfo(self):
        print("DriveRootContent.queryCreatableContentsInfo():*************************")
        return self._getCreatableContentsInfo()
    def createNewContent(self, contentinfo):
        print("DriveRootContent.createNewContent():************************* %s" % contentinfo)
        pass

    # XContent
    def getIdentifier(self):
        print("DriveRootContent.getIdentifier()")
        identifier = '%s://%s/%s' % (self.Scheme, self.UserName, self.Id)
        return queryContentIdentifier(self.ctx, identifier)
    def getContentType(self):
        print("DriveRootContent.getContentType()")
        return 'application/vnd.google-apps.folder-root'
    def addContentEventListener(self, listener):
        print("DriveRootContent.addContentEventListener()")
        self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        print("DriveRootContent.removeContentEventListener()")
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)

    # XCommandProcessor2
    def createCommandIdentifier(self):
        return 0
    def execute(self, command, id, environment):
        try:
            print("DriveRootContent.execute(): %s" % command.Name)
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
                print("DriveRootContent.execute() setPropertyValues: %s" % (arguments, ))
                return tuple(results)
            elif command.Name == 'open':
                print("DriveRootContent.execute() open 1")
                if not self.IsInCache:
                    updateChildren(self.ctx, self.Scheme, self.UserName, self.Id)
                    print("DriveRootContent.execute() open 2")
                    self.IsInCache = True
                    print("DriveRootContent.execute() open 3")
                return DynamicResultSet(self.ctx, self.Scheme, self.UserName, self.Id, command.Argument)
            elif command.Name == 'createNewContent':
                if command.Argument.Type == 'application/vnd.google-apps.folder':
                    print("DriveRootContent.execute(): createNewContent %s" % command.Argument)
                    id = getNewId(self.authentication, self.IdSelect, self.UserName)
                    kwargs = {'Scheme': self.Scheme, 'UserName': self.UserName, 'Id': id, 'ParentId': self.Id, 'NewItem': True}
                    name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'
                    content = createService(name, self.ctx, **kwargs)
                    return content
            elif command.Name == 'insert':
                print("DriveRootContent.execute(): insert")
                #id = gdrive.getNewIdentifier(self.auth, self.url, self.Title, self.MediaType, self.ParentsId)
                #if id is not None:
                #    self.Id = id
                #    identifier = gdrive.queryContentIdentifier(self.ctx, self.Scheme, self.UserName, self.ParentsId[0])
                #    action = uno.getConstantByName('com.sun.star.ucb.ContentAction.INSERTED')
                #    event = gdrive.getContentEvent(action, self, identifier)
                #    parent = gdrive.getUcb(self.ctx).queryContent(identifier)
                #    parent.notify(event)
            elif command.Name == 'delete':
                print("DriveRootContent.execute(): delete")
            elif command.Name == 'transfer':
                source = command.Argument.SourceURL
                sf = getSimpleFile(self.ctx)
                if sf.exists(source):
                    id = command.Argument.NewTitle
                    target = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, id))
                    inputstream = sf.openFileRead(source)
                    sf.writeFile(target, inputstream)
                    inputstream.closeInput()
                    #self.Size = sf.getSize(target)
                    if command.Argument.MoveData:
                        pass #must delete object
            elif command.Name == 'close':
                print("DriveRootContent.execute(): close")
        except Exception as e:
            print("DriveRootContent.execute().Error: %s - %e" % (e, traceback.print_exc()))
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
                print("DriveRootContent._getPropertyValues().Error: %s " % (property.Name, ))
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
        properties['ContentType'] = getProperty('ContentType', 'string', readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', readonly)
        properties['Title'] = getProperty('Title', 'string', transient)
        properties['Size'] = getProperty('Size', 'long', readonly)
        properties['DateModified'] = getProperty('DateModified', 'com.sun.star.util.DateTime', readonly)
        properties['DateCreated'] = getProperty('DateCreated', 'com.sun.star.util.DateTime', readonly)
        properties['IsInCache'] = getProperty('IsInCache', 'boolean', readonly)
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


g_ImplementationHelper.addImplementation(DriveRootContent,                                                   # UNO object class
                                         g_ImplementationName,                                               # Implementation name
                                        (g_ImplementationName, ))                                            # List of implemented services
