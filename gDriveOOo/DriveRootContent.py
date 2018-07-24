#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.awt import XCallback
from com.sun.star.ucb import XContent, XCommandProcessor2, XContentCreator, IllegalIdentifierException

import gdrive
from gdrive import PyComponent, PyInitialization, PyPropertyContainer, PyDynamicResultSet
from gdrive import PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier
import requests
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveRootContent'


class DriveRootContent(unohelper.Base, XServiceInfo, PyComponent, PyInitialization,
                       PyPropertyContainer, XContent, XCommandProcessor2, XContentCreator, XCallback,
                       PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier):
    def __init__(self, ctx, *namedvalues):
        try:
            self.ctx = ctx
            self.Scheme = None
            self.UserName = None
            self.Connection = None
            self.FileId = None

            self.listeners = []
            self.contentListeners = []
            #PyPropertiesChangeNotifier listeners
            self.propertiesListener = {}
            #XPropertySetInfoChangeNotifier listeners
            self.propertyInfoListeners = []
            #XCommandInfoChangeNotifier listeners
            self.commandInfoListeners = []
            self.properties = self._getPropertySetInfo()
            self.commands = self._getCommandInfo()
            
            self.initialize(namedvalues)
            
            self.ItemSelect = gdrive.getItemSelectStatement(self.Connection, self.Scheme, self.UserName, self.FileId)
            self.ItemUpdate = gdrive.getItemUpdateStatement(self.Connection, self.FileId)
            self.ChildSelect = gdrive.getChildSelectStatement(self.Connection, self.Scheme, self.UserName, self.FileId)
            
            self.authentication = gdrive.OAuth2Ooo(self.ctx, self.Scheme, self.UserName)
            print("DriveRootContent.__init__()")
        except Exception as e:
            print("DriveRootContent.__init__().Error: %s - %s" % (e, traceback.print_exc()))

    # XCallback
    def notify(self, data):
        if data.Action == uno.getConstantByName('com.sun.star.ucb.ContentAction.INSERTED'):
            properties = {'FileId': 'id', 'Title': 'name', 'Size': 'size',
                          'MediaType': 'mimeType', 'ParentsId': 'parents', 'DateModified': 'modifiedTime'}
            values = gdrive.geContentValues(data.Content, properties)
            #self.ResultSet.append(values)
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
        print("DriveRootContent.getIdentifier() %s" % self.FileId)
        return gdrive.queryContentIdentifier(self.ctx, self.Scheme, self.UserName, self.FileId)
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
                return gdrive.PyCommandInfo(self.commands)
            elif command.Name == 'getPropertySetInfo':
                return gdrive.PyPropertySetInfo(self.properties)
            elif command.Name == 'getPropertyValues':
                return gdrive.Row(self.ItemSelect, command.Argument)
            elif command.Name == 'setPropertyValues':
                result = []
                arguments = {}
                for property in command.Argument:
                    if hasattr(property, 'Name') and hasattr(property, 'Value'):
                        arguments[property.Name] = property.Value
                    result.append(None)
                self.setItem(arguments)
                return result
            elif command.Name == 'open':
                print("DriveRootContent.execute() open 1")
                if not self._getIsInCache():
                    gdrive.updateChildren(self.authentication, self.Connection, self.ItemUpdate, self.FileId)
                    self._setItem({'IsInCache': True})
                    print("DriveRootContent.execute() open2")
                return gdrive.DynamicResultSet(self.ctx, self.ChildSelect, command.Argument)
            elif command.Name == 'createNewContent':
                if command.Argument.Type == 'application/vnd.google-apps.folder':
                    arguments = {'ParentsId': [self.FileId], 'UserName': self.UserName}
                    name = 'com.gmail.prrvchr.extensions.gDriveOOo.GoogleDriveFolderContent'
                    content = gdrive.createService(name, self.ctx, **arguments)
                    return content
            elif command.Name == 'insert':
                id = gdrive.getNewIdentifier(self.auth, self.url, self.Title, self.MediaType, self.ParentsId)
                if id is not None:
                    self.FileId = id
                    identifier = gdrive.queryContentIdentifier(self.ctx, self.Scheme, self.UserName, self.ParentsId[0])
                    action = uno.getConstantByName('com.sun.star.ucb.ContentAction.INSERTED')
                    event = gdrive.getContentEvent(action, self, identifier)
                    parent = gdrive.getUcb(self.ctx).queryContent(identifier)
                    parent.notify(event)
            elif command.Name == 'delete':
                print("DriveRootContent.execute(): delete")
            elif command.Name == 'transfer':
                source = command.Argument.SourceURL
                sf = gdrive.getSimpleFile(self.ctx)
                if sf.exists(source):
                    id = command.Argument.NewTitle
                    target = gdrive.getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, id))
                    inputstream = sf.openFileRead(source)
                    sf.writeFile(target, inputstream)
                    inputstream.closeInput()
                    size = sf.getSize(target)
                    self._setItem({'Size': size, 'Updated': True}, id)
                    if command.Argument.MoveData:
                        pass #must delete object
        except Exception as e:
            print("DriveRootContent.execute().Error: %s - %e" % (e, traceback.print_exc()))
    def abort(self, id):
        pass
    def releaseCommandIdentifier(self, id):
        pass

    def _setItem(self, values={}, id=None):
        id = self.FileId if id is None else id
        return gdrive.updateItem(self.ItemUpdate, self.ItemSelect, id, values)

    def _getIsInCache(self):
        result = self.ItemSelect.executeQuery()
        result.next()
        return result.getColumns().getByName('IsInCache').getBoolean()

    def _getCommandInfo(self):
        commands = {}
        commands['getCommandInfo'] = gdrive.getCommand('getCommandInfo')
        commands['getPropertySetInfo'] = gdrive.getCommand('getPropertySetInfo')
        commands['getPropertyValues'] = gdrive.getCommand('getPropertyValues', '[]com.sun.star.beans.Property')
        commands['setPropertyValues'] = gdrive.getCommand('setPropertyValues', '[]com.sun.star.beans.PropertyValue')
        commands['open'] = gdrive.getCommand('open', 'com.sun.star.ucb.OpenCommandArgument2')
        commands['insert'] = gdrive.getCommand('insert', 'com.sun.star.ucb.InsertCommandArgument')
#        commands['createNewContent'] = gdrive.getCommand('createNewContent', 'com.sun.star.ucb.ContentInfo')
        commands['transfer'] = gdrive.getCommand('transfer', 'com.sun.star.ucb.TransferInfo')
        return commands

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['FileId'] = gdrive.getProperty('FileId', 'string', readonly)
        properties['ContentType'] = gdrive.getProperty('ContentType', 'string', readonly)
        properties['MediaType'] = gdrive.getProperty('MediaType', 'string', readonly)
        properties['IsDocument'] = gdrive.getProperty('IsDocument', 'boolean', readonly)
        properties['IsFolder'] = gdrive.getProperty('IsFolder', 'boolean', readonly)
        properties['Title'] = gdrive.getProperty('Title', 'string', transient)
        properties['Size'] = gdrive.getProperty('Size', 'long', readonly)
        properties['DateModified'] = gdrive.getProperty('DateModified', 'com.sun.star.util.DateTime', readonly)
        properties['DateCreated'] = gdrive.getProperty('DateCreated', 'com.sun.star.util.DateTime', readonly)
#        properties['CreatableContentsInfo'] = gdrive.getProperty('CreatableContentsInfo', '[]com.sun.star.ucb.ContentInfo', readonly)
        return properties

    def _getCreatableContentsInfo(self):
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        document = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_DOCUMENT')
        folder = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_FOLDER')
        ctype = 'application/vnd.google-apps.folder'
        properties = (gdrive.getProperty('Title', 'string', transient), )
        content = (gdrive.getContentInfo(ctype, folder, properties), )
        return content

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(DriveRootContent,                          # UNO object class
                                         g_ImplementationName,                      # Implementation name
                                        (g_ImplementationName,))                    # List of implemented services
