#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.awt import XCallback
from com.sun.star.container import XChild
from com.sun.star.lang import XServiceInfo, NoSupportException
from com.sun.star.ucb import XContent, XCommandProcessor2, XContentCreator
from com.sun.star.ucb import InteractiveBadTransferURLException, CommandAbortedException
from com.sun.star.ucb.ContentAction import INSERTED, REMOVED, DELETED, EXCHANGED
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE

from gdrive import Initialization, CommandInfo, PropertySetInfo, Row, DynamicResultSet, PropertyContainer
from gdrive import PropertiesChangeNotifier, PropertySetInfoChangeNotifier, CommandInfoChangeNotifier
from gdrive import getDbConnection, getNewIdentifier, propertyChange, getChildSelect, parseDateTime, getLogger, getUcp
from gdrive import createService, getSimpleFile, getResourceLocation, isChildId, selectChildId
from gdrive import getUcb, getCommandInfo, getProperty, getContentInfo, setContentProperties, createContent
from gdrive import getCommandIdentifier, getContentEvent, ContentIdentifier
from gdrive import getPropertiesValues, setPropertiesValues, g_folder
from gdrive import RETRIEVED, CREATED, FOLDER, FILE, RENAMED, REWRITED, TRASHED


import requests
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveFolderContent'


class DriveFolderContent(unohelper.Base, XServiceInfo, Initialization, XContent, XChild,
                         XCommandProcessor2, XContentCreator, PropertyContainer, PropertiesChangeNotifier,
                         PropertySetInfoChangeNotifier, CommandInfoChangeNotifier, XCallback):
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
            self.MimeType = 'application/vnd.google-apps.folder'
            self.Size = 0
            self._Trashed = False

            self.CanAddChild = True
            self.CanRename = True
            self.IsReadOnly = False
            self.IsVersionable = False
            self._Loaded = 1

            self.IsHidden = False
            self.IsVolume = False
            self.IsRemote = False
            self.IsRemoveable = False
            self.IsFloppy = False
            self.IsCompactDisc = False

            self.listeners = []
            self.contentListeners = []
            self.propertiesListener = {}
            self.propertyInfoListeners = []
            self.commandInfoListeners = []
            self.commandIdentifier = 0

            self.initialize(namedvalues)

            self._commandInfo = self._getCommandInfo()
            self._propertySetInfo = self._getPropertySetInfo()
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
    def UserName(self):
        return self.Identifier.User.Name
    @property
    def Title(self):
        return self.Name
    @Title.setter
    def Title(self, title):
        identifier = self.getIdentifier()
        old = self.Name
        self.Name = title
        propertyChange(self, 'Name', old, title)
        event = getContentEvent(self, EXCHANGED, self, identifier)
        self.notify(event)
    @property
    def Trashed(self):
        return self._Trashed
    @Trashed.setter
    def Trashed(self, trashed):
        propertyChange(self, 'Trashed', self._Trashed, trashed)
    @property
    def MediaType(self):
        return self.MimeType
    @property
    def Loaded(self):
        return self._Loaded
    @Loaded.setter
    def Loaded(self, loaded):
        propertyChange(self, 'Loaded', self._Loaded, loaded)
        self._Loaded = loaded
    @property
    def CreatableContentsInfo(self):
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

    # XCallback
    def notify(self, event):
        for listener in self.contentListeners:
            print("DriveFolderContent.notify() ***********************************************")
            listener.contentEvent(event)

    # XContentCreator
    def queryCreatableContentsInfo(self):
        print("DriveFolderContent.queryCreatableContentsInfo():*************************")
        return self.CreatableContentsInfo
    def createNewContent(self, contentinfo):
        id = self.getIdentifier()
        uri = '%s/%s' % (id.BaseURL, id.NewIdentifier)
        identifier = ContentIdentifier(self.ctx, id.Connection, id.Mode, id.User, uri, True)
        print("DriveFolderContent.createNewContent():\nNew Uri: %s\nBaseURL: %s\nUri: %s" % (uri, id.BaseURL, id.getContentIdentifier()))
        kwarg = {'Identifier': identifier, 'MimeType': contentinfo.Type}
        content = createContent(self.ctx, kwarg)
        return content

    # XChild
    def getParent(self):
        if self.Identifier.IsRoot:
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
        print("DriveFolderContent.addContentEventListener():*************************")
        self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        print("DriveFolderContent.removeContentEventListener():*************************")
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)

    # XCommandProcessor2
    def createCommandIdentifier(self):
        print("DriveFolderContent.createCommandIdentifier(): **********************")
        return getCommandIdentifier(self)
    def execute(self, command, id, environment):
        #try:
        print("DriveFolderContent.execute(): %s - %s" % (command.Name, id))
        if command.Name == 'getCommandInfo':
            return CommandInfo(self._commandInfo)
        elif command.Name == 'getPropertySetInfo':
            return PropertySetInfo(self._propertySetInfo)
        elif command.Name == 'getPropertyValues':
            namedvalues = getPropertiesValues(self, command.Argument, self.Logger)
            return Row(namedvalues)
        elif command.Name == 'setPropertyValues':
            return setPropertiesValues(self, command.Argument, self._propertySetInfo, self.Logger)
        elif command.Name == 'open':
            print("DriveFolderContent.execute() open 1")
            if self.Loaded == ONLINE:
                self.Identifier.updateLinks()
                if self.Identifier.Updated:
                    self.Loaded = OFFLINE
            print("DriveFolderContent.execute() open 2")
            # Not Used: command.Argument.Properties - Implement me ;-)
            index, select = getChildSelect(self.Identifier)
            print("DriveFolderContent.execute() open 3")
            return DynamicResultSet(self.ctx, self.Identifier, select, index)
            print("DriveFolderContent.execute() open 4")
        elif command.Name == 'insert':
            print("DriveFolderContent.execute() insert")
            ucp = getUcp(self.ctx)
            self.addPropertiesChangeListener(('Id', 'Name', 'Size', 'Trashed', 'Loaded'), ucp)
            self.Id = CREATED + FOLDER
            identifier = self.getIdentifier().getParent()
            event = getContentEvent(self, INSERTED, self, identifier)
            ucp.queryContent(identifier).notify(event)
        elif command.Name == 'delete':
            print("DriveFolderContent.execute(): delete")
            self.Trashed = True
        elif command.Name == 'createNewContent':
            print("DriveFolderContent.execute(): createNewContent %s" % command.Argument)
            return self.createNewContent(command.Argument)
        elif command.Name == 'transfer':
            # Transfer command is only used for existing document (File Save)
            # NewTitle come from:
            # - Last segment path of "XContent.getIdentifier().getContentIdentifier()" for OpenOffice
            # - Property Title of "XContent" for LibreOffice
            # If the content has been renamed, the last segment is the new Title of the content
            # We assume 'command.Argument.NewTitle' as an id
            id = command.Argument.NewTitle
            source = command.Argument.SourceURL
            clash = command.Argument.NameClash
            print("DriveFolderContent.execute(): transfer 1:\n    %s - %s - %s - %s" % (source, id, command.Argument.MoveData, clash))
            if not isChildId(self.Identifier, id):
                # It appears that 'command.Argument.NewTitle' is not an id but a title...
                # If 'NewTitle' exist and is unique in the folder, we can retrieve its Id
                id = selectChildId(self.Identifier.Connection, self.Identifier.Id, id)
                if id is None:
                    print("DriveFolderContent.execute(): transfer 2:\n    create NewIdentifier: %s - %s" % (source, id))
                    if not hasattr(command.Argument, 'DocumentId'):
                        print("DriveFolderContent.execute(): transfer 3:\n    create NewIdentifier: %s - %s" % (source, id))
                        raise InteractiveBadTransferURLException("Couln't handle Url: %s" % source, self)
                    # Id could not be found: NewTitle does not exist or is not unique in the folder
                    # For new document (File Save As) we use commands:
                    # createNewContent: for creating an empty new Content
                    # Insert at new Content for committing change
                    # For accessing this commands we must trow an "InteractiveBadTransferURLException"
                    print("DriveFolderContent.execute(): transfer 4:\n    create NewIdentifier: %s - %s" % (command.Argument.DocumentId, command.Argument.MimeType))
            print("DriveFolderContent.execute(): transfer 2:\n    transfer: %s - %s" % (source, id))
            sf = getSimpleFile(self.ctx)
            if not sf.exists(source):
                raise CommandAbortedException("Error while saving file: %s" % source, self)
            target = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, id))
            stream = sf.openFileRead(source)
            sf.writeFile(target, stream)
            stream.closeInput()
            ucb = getUcb(self.ctx)
            identifier = ucb.createContentIdentifier('%s/%s' % (self.Identifier.BaseURL, id))
            setContentProperties(ucb.queryContent(identifier), {'Size': sf.getSize(target)})
            print("DriveFolderContent.execute(): transfer 3: Fin")
            if command.Argument.MoveData:
                pass #must delete object
        elif command.Name == 'close':
            print("DriveFolderContent.execute(): close")
        elif command.Name == 'flush':
            print("DriveFolderContent.execute(): flush")
        #except Exception as e:
        #    print("DriveFolderContent.execute().Error: %s - %e" % (e, traceback.print_exc()))

    def abort(self, id):
        print("DriveFolderContent.abort(): %s" % id)
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
        #commands['insert'] = getCommandInfo('insert', 'com.sun.star.ucb.InsertCommandArgument2')
        if not self.Identifier.IsRoot:
            commands['delete'] = getCommandInfo('delete', 'boolean')
        commands['transfer'] = getCommandInfo('transfer', 'com.sun.star.ucb.TransferInfo')
        commands['close'] = getCommandInfo('close')
        commands['flush'] = getCommandInfo('flush')
        return commands

    def _getPropertySetInfo(self):
        properties = {}
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        constrained = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.CONSTRAINED')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['Id'] = getProperty('Id', 'string', bound | readonly)
#        properties['ParentsId'] = getProperty('ParentsId', '[]string', bound | readonly)
        properties['ContentType'] = getProperty('ContentType', 'string', bound | readonly)
        properties['MimeType'] = getProperty('MimeType', 'string', bound | readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', bound | readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', bound | readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', bound | readonly)
        properties['Title'] = getProperty('Title', 'string', bound | constrained)
        properties['Size'] = getProperty('Size', 'long', bound | readonly)
        properties['DateModified'] = getProperty('DateModified', 'com.sun.star.util.DateTime', bound | readonly)
        properties['DateCreated'] = getProperty('DateCreated', 'com.sun.star.util.DateTime', bound | readonly)
        properties['Loaded'] = getProperty('Loaded', 'long', bound)
        properties['CreatableContentsInfo'] = getProperty('CreatableContentsInfo', '[]com.sun.star.ucb.ContentInfo', bound | readonly)

        properties['IsHidden'] = getProperty('IsHidden', 'boolean', bound | readonly)
        properties['IsVolume'] = getProperty('IsVolume', 'boolean', bound | readonly)
        properties['IsRemote'] = getProperty('IsRemote', 'boolean', bound | readonly)
        properties['IsRemoveable'] = getProperty('IsRemoveable', 'boolean', bound | readonly)
        properties['IsFloppy'] = getProperty('IsFloppy', 'boolean', bound | readonly)
        properties['IsCompactDisc'] = getProperty('IsCompactDisc', 'boolean', bound | readonly)
        return properties

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
