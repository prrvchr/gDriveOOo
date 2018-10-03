#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.container import XChild
from com.sun.star.lang import XServiceInfo, NoSupportException
from com.sun.star.ucb import XContent, XCommandProcessor2, XContentCreator
from com.sun.star.ucb import InteractiveBadTransferURLException, CommandAbortedException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE

from gdrive import Initialization, CommandInfo, PropertySetInfo, Row, DynamicResultSet
from gdrive import PropertiesChangeNotifier, PropertySetInfoChangeNotifier, CommandInfoChangeNotifier
from gdrive import getDbConnection, propertyChange, getChildSelect, parseDateTime, getPropertiesValues, getLogger

from gdrive import updateChildren, createService, getSimpleFile, getResourceLocation, isChild
from gdrive import getUcb, getCommandInfo, getProperty, getContentInfo, setContentProperties
from gdrive import getContentEvent, setPropertiesValues, updateMetaData, updateData
from gdrive import getUcp, uploadItem, getSession, unparseDateTime
from gdrive import g_folder

import requests
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'


class DriveFolderContent(unohelper.Base, XServiceInfo, Initialization, XContent, XChild, XCommandProcessor2,
                         XContentCreator, PropertiesChangeNotifier, PropertySetInfoChangeNotifier, CommandInfoChangeNotifier):
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
            self.IsRoot = False
            self.IsFolder = True
            self.IsDocument = False
            self.DateCreated = parseDateTime()
            self.DateModified = parseDateTime()
            self.MimeType = 'application/vnd.google-apps.folder'
            self.Size = 0
            
            self._SyncMode = 0
            
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
            
            self.Connection = None
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
    def SyncMode(self):
        return self._SyncMode
    @SyncMode.setter
    def SyncMode(self, mode):
        old = self._SyncMode
        self._SyncMode |= mode
        if self._SyncMode != old:
            propertyChange(self, 'SyncMode', old, self._SyncMode)
    @property
    def MediaType(self):
        return self.MimeType

    # XContentCreator
    def queryCreatableContentsInfo(self):
        print("DriveFolderContent.queryCreatableContentsInfo():*************************")
        return self.CreatableContentsInfo
    def createNewContent(self, contentinfo):
        print("DriveFolderContent.createNewContent(): 1 - %s" % self._NewTitle)
        id = getUcb(self.ctx).createContentIdentifier('%s#' % self.Identifier.getContentIdentifier())
        data = {'Identifier': id}
        if contentinfo.Type == g_folder:
            data.update({'Connection': self.Connection})
            name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'
        elif contentinfo.Type == 'application/vnd.oasis.opendocument':
            data.update({'Name': self._NewTitle})
            name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveOfficeContent'
        elif contentinfo.Type == 'application/vnd.google-apps.document':
            data.update({'Name': self._NewTitle})
            name = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveDocumentContent'            
        content = createService(name, self.ctx, **data)
        print("DriveFolderContent.createNewContent(): 2")
        return content

    # XChild
    def getParent(self):
        if self.IsRoot:
            raise NoSupportException('Root Folder as no Parent', self)
        print("DriveFolderContent.getParent()")
        identifier = self.Identifier.getParent()
        return getUcb(self.ctx).queryContent(identifier)
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
            mode = self.Identifier.ConnectionMode
            if mode == ONLINE and self.SyncMode == ONLINE:
                with getSession(self.ctx, self.Identifier.UserName) as session:
                    self.SyncMode = updateChildren(self.Connection, session, self.Identifier)
            # Not Used: command.Argument.Properties - Implement me ;-)
            index, select = getChildSelect(self.Connection, self.Identifier)
            return DynamicResultSet(self.ctx, self.Scheme, select, index)
        elif command.Name == 'createNewContent':
            print("DriveFolderContent.execute(): createNewContent %s" % command.Argument)
            return self.createNewContent(command.Argument)
        elif command.Name == 'insert':
            print("DriveFolderContent.execute() insert")
            #identifier = self.Identifier.getParent()
            #action = uno.getConstantByName('com.sun.star.ucb.ContentAction.INSERTED')
            #event = getContentEvent(action, self, identifier)
            if self.Identifier.ConnectionMode == ONLINE:
                updateMetaData(self.ctx, self, 20)
            else:
                self.SyncMode = 20
            self.addPropertiesChangeListener(('Id', 'SyncMode', 'Name', 'Size'), getUcp(self.ctx))
            self.Id = self.Id
        elif command.Name == 'delete':
            print("DriveFolderContent.execute(): delete")
        elif command.Name == 'transfer':
            # Transfer command is only used for existing document (File Save)
            id = command.Argument.NewTitle
            source = command.Argument.SourceURL
            print("DriveFolderContent.execute(): transfer: %s - %s" % (source, id))
            if not isChild(self.Connection, id, self.Id):
                # For new document (File Save As) we use command: createNewContent and Insert
                self._NewTitle = id
                print("DriveFolderContent.execute(): transfer copy: %s - %s" % (source, id))
                raise InteractiveBadTransferURLException("Couln't handle Url: %s" % source, self)
            print("DriveFolderContent.execute(): transfer: %s - %s" % (source, id))
            sf = getSimpleFile(self.ctx)
            if not sf.exists(source):
                raise CommandAbortedException("Error while saving file: %s" % source, self)
            target = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, id))
            stream = sf.openFileRead(source)
            sf.writeFile(target, stream)
            stream.closeInput()
            ucb = getUcb(self.ctx)
            # Folder Uri end whith it's Id: ie: 'scheme://authority/.../parentId/folderId'
            identifier = self.Identifier.getContentIdentifier()
            identifier = '%s%s' % (identifier, id) if identifier.endswith('/') else '%s/%s' % (identifier, id)
            identifier = ucb.createContentIdentifier(identifier)
            content = ucb.queryContent(identifier)
            size = sf.getSize(target)
            updated = {'Size': size}
            if self.Identifier.ConnectionMode == ONLINE:
                stream = sf.openFileRead(target)
                updateData(self.ctx, content, 8, stream, size)
            else:
                updated.update({'SyncMode': 8})
            setContentProperties(content, updated)
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
        properties['MimeType'] = getProperty('MimeType', 'string', bound | readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', bound | readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', bound | readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', bound | readonly)
        properties['Title'] = getProperty('Title', 'string', bound)
        properties['Size'] = getProperty('Size', 'long', bound | readonly)
        properties['DateModified'] = getProperty('DateModified', 'com.sun.star.util.DateTime', bound | readonly)
        properties['DateCreated'] = getProperty('DateCreated', 'com.sun.star.util.DateTime', bound | readonly)
        properties['SyncMode'] = getProperty('SyncMode', 'long', bound)
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
            officetype = 'application/vnd.oasis.opendocument'
            documenttype = 'application/vnd.google-apps.document'
            properties = (getProperty('Title', 'string', bound), )
            content = (getContentInfo(foldertype, folder, properties),
                       getContentInfo(officetype, document, properties),
                       getContentInfo(documenttype, document, properties))
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
