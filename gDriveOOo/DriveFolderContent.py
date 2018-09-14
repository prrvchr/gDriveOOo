#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.awt import XCallback
from com.sun.star.beans import XPropertyContainer
from com.sun.star.container import XChild
from com.sun.star.lang import XServiceInfo, NoSupportException
from com.sun.star.ucb import XContent, XCommandProcessor2, XContentCreator, IllegalIdentifierException
from com.sun.star.ucb import InteractiveBadTransferURLException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE

from gdrive import Component, Initialization, CommandInfo, PropertySetInfo, DynamicResultSet, ContentIdentifier
from gdrive import PropertiesChangeNotifier, PropertySetInfoChangeNotifier, CommandInfoChangeNotifier, Row
from gdrive import getDbConnection, propertyChange, getChildSelect, parseDateTime, getPropertiesValues, getLogger

from gdrive import updateChildren, createService, getSimpleFile, getResourceLocation, isChild
from gdrive import getUcb, getCommandInfo, getProperty, getContentInfo, setContentProperties
from gdrive import getContent, getContentEvent, setPropertiesValues
from gdrive import getUcp, createNewContent, uploadItem, getSession

import requests
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'


class DriveFolderContent(unohelper.Base, XServiceInfo, Component, Initialization, PropertiesChangeNotifier,
                         XContent, XCommandProcessor2, XContentCreator, XChild, XCallback,
                         PropertySetInfoChangeNotifier, XPropertyContainer, CommandInfoChangeNotifier):
    def __init__(self, ctx, *namedvalues):
        try:
            self.ctx = ctx
            self.Logger = getLogger(self.ctx)
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            msg = "DriveFolderContent loading ..."
            self.Logger.logp(level, "DriveFolderContent", "__init__()", msg)
            self.Identifier = None

            self.ContentType = 'application/vnd.google-apps.folder'
            self.Name = 'Sans Nom'
            self.IsFolder = True
            self.IsDocument = False
            self.DateCreated = parseDateTime()
            self.DateModified = parseDateTime()
            self.MediaType = 'application/vnd.google-apps.folder'
            self.Size = 0
            
            self._IsRead = False
            self._IsWrite = False
            
            self.CanAddChild = False
            self.CanRename = False
            self.IsReadOnly = True
            self.IsVersionable = False
            
            self._NewTitle = ''

            self.IsHidden = False
            self.IsVolume = False
            self.IsRemote = False
            self.IsRemoveable = False
            self.IsFloppy = False
            self.IsCompactDisc = False
            
            self._commandInfo = self._getCommandInfo()
            self._propertySetInfo = self._getPropertySetInfo()
            self.listeners = []
            self.contentListeners = []
            self.propertiesListener = {}
            self.propertyInfoListeners = []
            self.commandInfoListeners = []
            
            self.Statement = None
            self.initialize(namedvalues)
            
            self.CreatableContentsInfo = self._getCreatableContentsInfo()
            msg = "DriveFolderContent loading Uri: %s ... Done" % self.Identifier.getContentIdentifier()
            self.Logger.logp(level, "DriveFolderContent", "__init__()", msg)
            print(msg)
        except Exception as e:
            print("DriveFolderContent.__init__().Error: %s - %e" % (e, traceback.print_exc()))

    @property
    def Id(self):
        return self.Identifier.Id
    @Id.setter
    def Id(self, id):
        propertyChange(self, 'Id', self.Id, id)
    @property
    def Scheme(self):
        return self.Identifier.getContentProviderScheme()
    @property
    def Title(self):
        return self.Name
    @Title.setter
    def Title(self, title):
        propertyChange(self, 'Name', self.Name, title)
        self.Name = title
    @property
    def IsRead(self):
        return self._IsRead
    @IsRead.setter
    def IsRead(self, isread):
        propertyChange(self, 'IsRead', self._IsRead, isread)
        self._IsRead = isread
    @property
    def IsWrite(self):
        return self._IsWrite
    @IsWrite.setter
    def IsWrite(self, iswrite):
        propertyChange(self, 'IsWrite', self._IsWrite, iswrite)
        self._IsWrite = iswrite

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
        print("DriveFolderContent.createNewContent():************************* %s" % self._NewTitle)
        return createNewContent(self.ctx, self.Statement, self.Identifier.getContentIdentifier(), contentinfo, self._NewTitle)

    # XChild
    def getParent(self):
        print("DriveFolderContent.getParent()")
        identifier = self.Identifier.getParent()
        return getContent(self.ctx, identifier)
    def setParent(self, parent):
        print("DriveFolderContent.setParent()")
        raise NoSupportException('Parent can not be set', self)

    # XContent
    def getIdentifier(self):
        return self.Identifier
    def getContentType(self):
        return self.ContentType
    def addContentEventListener(self, listener):
        #print("DriveFolderContent.addContentEventListener():*************************")
        self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        #print("DriveFolderContent.removeContentEventListener():*************************")
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)

    # XCommandProcessor2
    def createCommandIdentifier(self):
        print("DriveFolderContent.createCommandIdentifier(): **********************")
        return 0
    def execute(self, command, id, environment):
        print("DriveFolderContent.execute(): %s" % command.Name)
        if command.Name == 'getCommandInfo':
            return CommandInfo(self._commandInfo)
        elif command.Name == 'getPropertySetInfo':
            return PropertySetInfo(self._propertySetInfo)
        elif command.Name == 'getPropertyValues':
            namedvalues = getPropertiesValues(self, command.Argument,self.Logger)
            return Row(namedvalues)
        elif command.Name == 'setPropertyValues':
            return setPropertiesValues(self, command.Argument, self.Logger)
        elif command.Name == 'open':
            connection = self.Statement.getConnection()
            mode = self.Identifier.ConnectionMode
            if mode == ONLINE and not self.IsRead:
                session = getSession(self.ctx, self.Scheme, self.Identifier.UserName)
                self.IsRead = updateChildren(connection, session, self.Identifier.UserId, self.Id)
            # Not Used: command.Argument.Properties - Implement me ;-)
            index, select = getChildSelect(connection, mode, self.Id, self.Identifier.getContentIdentifier(), False)
            return DynamicResultSet(self.ctx, self.Scheme, select, index)
        elif command.Name == 'createNewContent':
            print("DriveFolderContent.execute(): createNewContent %s" % command.Argument)
            return createNewContent(self.ctx, self.Statement, self.Identifier.getContentIdentifier(), command.Argument, self._NewTitle)
        elif command.Name == 'insert':
            print("DriveFolderContent.execute() insert")
            #identifier = self.Identifier.getParent()
            #action = uno.getConstantByName('com.sun.star.ucb.ContentAction.INSERTED')
            #event = getContentEvent(action, self, identifier)
            self.IsWrite = True
            ucp = getUcp(self.ctx, self.Identifier.getContentIdentifier())
            self.addPropertiesChangeListener(('Id', 'IsWrite', 'IsRead', 'Name', 'Size'), ucp)
            self.Id = self.Id
            if self.Identifier.ConnectionMode == ONLINE:
                pass
        elif command.Name == 'delete':
            print("DriveFolderContent.execute(): delete")
        elif command.Name == 'transfer':
            # Transfer command is only used for existing document (File Save)
            id = command.Argument.NewTitle
            source = command.Argument.SourceURL
            print("DriveFolderContent.execute(): transfer: %s - %s" % (source, id))
            if not isChild(self.Statement.getConnection(), id, self.Id):
                # For new document (File Save As) we use command: createNewContent and Insert
                self._NewTitle = id
                print("DriveFolderContent.execute(): transfer copy: %s - %s" % (source, id))
                raise InteractiveBadTransferURLException("Couln't handle Url: %s" % source, self)
            print("DriveFolderContent.execute(): transfer: %s - %s" % (source, id))
            sf = getSimpleFile(self.ctx)
            if sf.exists(source):
                target = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, id))
                stream = sf.openFileRead(source)
                sf.writeFile(target, stream)
                stream.closeInput()
                ucb = getUcb(self.ctx)
                # Folder Uri end whith it's Id: ie: 'scheme://authority/.../parentId/folderId'
                identifier = ucb.createContentIdentifier('%s/%s' % (self.Identifier.getContentIdentifier(), id))
                content = ucb.queryContent(identifier)
                size = sf.getSize(target)
                if self.Identifier.ConnectionMode == ONLINE:
                    stream = sf.openFileRead(target)
                    with getSession(self.ctx, self.Scheme, self.Identifier.UserName) as session:
                        uploadItem(self.ctx, session, stream, content, id, size, False)               
                else:
                    setContentProperties(content, {'Size': size, 'IsWrite': True})
                print("DriveFolderContent.execute(): transfer: Fin")
                if command.Argument.MoveData:
                    pass #must delete object
        elif command.Name == 'close':
            print("DriveFolderContent.execute(): close")
        elif command.Name == 'flush':
            print("DriveFolderContent.execute(): flush")
        #except Exception as e:
        #    print("DriveFolderContent.execute().Error: %s - %e" % (e, traceback.print_exc()))

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
#        commands['insert'] = getCommandInfo('insert', 'com.sun.star.ucb.InsertCommandArgument2')
        commands['delete'] = getCommandInfo('delete', 'boolean')
        commands['transfer'] = getCommandInfo('transfer', 'com.sun.star.ucb.TransferInfo')
        commands['close'] = getCommandInfo('close')
        commands['flush'] = getCommandInfo('flush')
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
        properties['IsRead'] = getProperty('IsRead', 'boolean', bound)
        properties['CreatableContentsInfo'] = getProperty('CreatableContentsInfo', '[]com.sun.star.ucb.ContentInfo', bound | readonly)

        properties['IsHidden'] = getProperty('IsHidden', 'boolean', bound | readonly)
        properties['IsVolume'] = getProperty('IsVolume', 'boolean', bound | readonly)
        properties['IsRemote'] = getProperty('IsRemote', 'boolean', bound | readonly)
        properties['IsRemoveable'] = getProperty('IsRemoveable', 'boolean', bound | readonly)
        properties['IsFloppy'] = getProperty('IsFloppy', 'boolean', bound | readonly)
        properties['IsCompactDisc'] = getProperty('IsCompactDisc', 'boolean', bound | readonly)
        return properties

    def _getCreatableContentsInfo(self):
        content = ()
        if self.CanAddChild:
            bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
            document = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_DOCUMENT')
            folder = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_FOLDER')
            foldertype = 'application/vnd.google-apps.folder'
            documenttype = 'application/vnd.oasis.opendocument'
            properties = (getProperty('Title', 'string', bound), )
            content = (getContentInfo(foldertype, folder, properties), getContentInfo(documenttype, document, properties))
        return content


    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(DriveFolderContent,                                                 # UNO object class
                                         g_ImplementationName,                                               # Implementation name
                                        (g_ImplementationName, 'com.sun.star.ucb.Content'))                  # List of implemented services
