#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.awt import XCallback
from com.sun.star.beans import XPropertyContainer
from com.sun.star.container import XChild
from com.sun.star.lang import XServiceInfo, NoSupportException
from com.sun.star.ucb import XContent, XCommandProcessor2, XContentCreator, IllegalIdentifierException

from gdrive import Component, Initialization, CommandInfo, PropertySetInfo, Row, DynamicResultSet
from gdrive import ContentIdentifier, PropertiesChangeNotifier
from gdrive import propertyChange, getChildSelect, parseDateTime, getPropertiesValues, getLogger

from gdrive import updateChildren, createService, getSimpleFile, getResourceLocation
from gdrive import getUcb, getCommandInfo, getProperty, getContentInfo
from gdrive import getContent, getContentEvent, getParentUri, setPropertiesValues
from gdrive import getId, getUri, getUriPath, getUcp, getNewItem

import requests
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'


class DriveFolderContent(unohelper.Base, XServiceInfo, Component, Initialization, PropertiesChangeNotifier,
                         XContent, XCommandProcessor2, XContentCreator, XChild, XCallback, XPropertyContainer):
    def __init__(self, ctx, *namedvalues):
        try:
            self.ctx = ctx
            self.Logger = getLogger(self.ctx)
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            msg = "DriveFolderContent loading ..."
            self.Logger.logp(level, "DriveFolderContent", "__init__()", msg)
            self.UserName = None
            self._Id = None
            self.Uri = None

            self.ContentType = 'application/vnd.google-apps.folder'
            self.IsFolder = True
            self.IsDocument = False
            self._Title = 'Sans Nom'
            
            self.MediaType = 'application/vnd.google-apps.folder'
            self.Size = 0
            self.DateModified = parseDateTime()
            self.DateCreated = parseDateTime()
            self._IsInCache = False
            self.CreatableContentsInfo = self._getCreatableContentsInfo()
            
            self.listeners = []
            self.contentListeners = []
            #PropertiesChangeNotifier listeners
            self.propertiesListener = {}
            #XPropertySetInfoChangeNotifier listeners
            self.propertyInfoListeners = []
            #XCommandInfoChangeNotifier listeners
            self.commandInfoListeners = []
            
            self.itemInsert = None
            self.itemUpdate = None
            self.childDelete = None
            self.childInsert = None
            self.initialize(namedvalues)
            msg = "DriveFolderContent loading Uri: %s ... Done" % self.Uri.getUriReference()
            self.Logger.logp(level, "DriveFolderContent", "__init__()", msg)
            print(msg)
        except Exception as e:
            print("DriveFolderContent.__init__().Error: %s - %e" % (e, traceback.print_exc()))

    @property
    def Id(self):
        return self._Id
    @Id.setter
    def Id(self, id):
        propertyChange(self, 'Id', self._Id, id)
        self._Id = id
    @property
    def IsInCache(self):
        return self._IsInCache
    @IsInCache.setter
    def IsInCache(self, state):
        propertyChange(self, 'IsInCache', self._IsInCache, state)
        self._IsInCache = state
    @property
    def Title(self):
        return self._Title
    @Title.setter
    def Title(self, title):
        propertyChange(self, 'Title', self._Title, title)
        self._Title = title

    # XPropertyContainer
    def addProperty(self, name, attribute, default):
        print("DriveFolderContent.addProperty()")
    def removeProperty(self, name):
        print("DriveFolderContent.removeProperty()")

    # XCallback
    def notify(self, data):
        for listener in self.contentListeners:
            listener.contentEvent(data)

    # XContentCreator
    def queryCreatableContentsInfo(self):
        print("DriveFolderContent.queryCreatableContentsInfo():*************************")
        return self.CreatableContentsInfo
    def createNewContent(self, contentinfo):
        print("DriveFolderContent.createNewContent():************************* %s" % contentinfo)
        pass

    # XChild
    def getParent(self):
        print("DriveFolderContent.getParent()")
        uri = getParentUri(self.ctx, self.Uri)
        identifier = ContentIdentifier(uri)
        return getContent(self.ctx, identifier)
    def setParent(self, parent):
        print("DriveFolderContent.setParent()")
        raise NoSupportException('Parent can not be set', self)

    # XContent
    def getIdentifier(self):
        return ContentIdentifier(self.Uri)
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
                namedvalues = getPropertiesValues(self, command.Argument,self.Logger)
                return Row(namedvalues)
            elif command.Name == 'setPropertyValues':
                return setPropertiesValues(self, command.Argument, self.Logger)
            elif command.Name == 'open':
                if not self.IsInCache:
                    updateChildren(self.ctx, self.itemInsert, self.itemUpdate, self.childDelete, 
                                   self.childInsert, self.Uri.getScheme(), self.UserName, self.Id)
                    self.IsInCache = True
                connection = self.childInsert.getConnection()
                select = getChildSelect(self.ctx, connection, self.Id, self.Uri.getUriReference(), command.Argument.Properties)
                return DynamicResultSet(self.ctx, self.Uri.getScheme(), select)
            elif command.Name == 'createNewContent':
                if command.Argument.Type == 'application/vnd.google-apps.folder':
                    print("DriveFolderContent.execute(): createNewContent %s" % command.Argument)
                    item = getNewItem(self.ctx, self.Uri, self.UserName)
                    name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'
                    content = createService(name, self.ctx, **item)
                    return content
            elif command.Name == 'insert':
                print("DriveFolderContent.execute() insert")
                #uri = getParentUri(self.ctx, self.Uri)
                #identifier = ContentIdentifier(uri)
                #action = uno.getConstantByName('com.sun.star.ucb.ContentAction.INSERTED')
                #event = getContentEvent(action, self, identifier)
                ucp = getUcp(self.ctx, self.Uri.getUriReference())
                self.addPropertiesChangeListener(('Id', 'IsInCache', 'Title', 'Size'), ucp)
                self.Id = self.Id
            elif command.Name == 'delete':
                print("DriveFolderContent.execute(): delete")
            elif command.Name == 'transfer':
                print("DriveRootContent.execute(): transfer")
                source = command.Argument.SourceURL
                sf = getSimpleFile(self.ctx)
                if sf.exists(source):
                    id = command.Argument.NewTitle
                    target = getResourceLocation(self.ctx, '%s/%s' % (self.Uri.getScheme(), id))
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
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['Id'] = getProperty('Id', 'string', bound | readonly)
#        properties['ParentsId'] = getProperty('ParentsId', '[]string', bound | readonly)
        properties['ContentType'] = getProperty('ContentType', 'string', bound | readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', bound | readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', bound | readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', bound | readonly)
        properties['Title'] = getProperty('Title', 'string', bound)
        properties['Size'] = getProperty('Size', 'long', bound | readonly)
        properties['DateModified'] = getProperty('DateModified', 'com.sun.star.util.DateTime', bound | readonly)
        properties['DateCreated'] = getProperty('DateCreated', 'com.sun.star.util.DateTime', bound | readonly)
        properties['IsInCache'] = getProperty('IsInCache', 'boolean', bound | readonly)
        properties['CreatableContentsInfo'] = getProperty('CreatableContentsInfo', '[]com.sun.star.ucb.ContentInfo', bound | readonly)
        return properties

    def _getCreatableContentsInfo(self):
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        document = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_DOCUMENT')
        folder = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_FOLDER')
        ctype = 'application/vnd.google-apps.folder'
        properties = (getProperty('Title', 'string', bound), )
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
