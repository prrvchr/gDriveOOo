#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.awt import XCallback
from com.sun.star.beans import XPropertyContainer
from com.sun.star.lang import XServiceInfo, XComponent
from com.sun.star.ucb import XContent, XCommandProcessor2, XContentCreator
from com.sun.star.ucb import InteractiveBadTransferURLException, IllegalIdentifierException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE

from gdrive import Initialization, CommandInfo, PropertySetInfo, Row, DynamicResultSet, ContentIdentifier
from gdrive import PropertySetInfoChangeNotifier, PropertiesChangeNotifier, CommandInfoChangeNotifier
from gdrive import getDbConnection, parseDateTime, isChild, getChildSelect, getLogger
from gdrive import updateChildren, createService, getSimpleFile, getResourceLocation
from gdrive import getUcb, getCommandInfo, getProperty, getContentInfo, getContent
from gdrive import propertyChange, getPropertiesValues, setPropertiesValues, uploadItem
from gdrive import createNewContent, setContentProperties, getSession

#from gdrive import PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier, PyPropertyContainer, PyDynamicResultSet
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveRootContent'


class DriveRootContent(unohelper.Base, XServiceInfo, XComponent, Initialization, PropertiesChangeNotifier, XContent,
                       PropertySetInfoChangeNotifier, XCommandProcessor2, XContentCreator, XCallback,
                       CommandInfoChangeNotifier, XPropertyContainer):
    def __init__(self, ctx, *namedvalues):
        try:
            self.ctx = ctx
            self.Logger = getLogger(self.ctx)
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            msg = "DriveRootContent loading ..."
            self.Logger.logp(level, "DriveRootContent", "__init__()", msg)
            self.Identifier = None
            
            self.ContentType = 'application/vnd.google-apps.folder-root'
            self.Name = 'Sans Nom'
            self.IsFolder = True
            self.IsDocument = False
            self.DateCreated = parseDateTime()
            self.DateModified = parseDateTime()
            self.MediaType = 'application/vnd.google-apps.folder'
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
            
            self.Statement = None
            self.initialize(namedvalues)
            self.CreatableContentsInfo = self._getCreatableContentsInfo()
            msg = "DriveRootContent loading Uri: %s ... Done" % self.Identifier.getContentIdentifier()
            self.Logger.logp(level, "DriveRootContent", "__init__()", msg)
            print("DriveRootContent.__init__()")
        except Exception as e:
            print("DriveRootContent.__init__().Error: %s - %s" % (e, traceback.print_exc()))

    @property
    def Id(self):
        return self.Identifier.Id
    @property
    def Scheme(self):
        return self.Identifier.getContentProviderScheme()
    @property
    def Title(self):
        return self.Name
    @property
    def SyncMode(self):
        return self._SyncMode
    @SyncMode.setter
    def SyncMode(self, mode):
        old = self._SyncMode
        self._SyncMode |= mode
        if self._SyncMode != old:
            propertyChange(self, 'SyncMode', old, self._SyncMode)
    # XPropertyContainer
    def addProperty(self, name, attribute, default):
        print("DriveRootContent.addProperty()")
    def removeProperty(self, name):
        print("DriveRootContent.removeProperty()")

    # XComponent
    def dispose(self):
        print("DriveRootContent.dispose()")
        event = uno.createUnoStruct('com.sun.star.lang.EventObject', self)
        for listener in self.listeners:
            listener.disposing(event)
    def addEventListener(self, listener):
        print("DriveRootContent.addEventListener()")
        if listener not in self.listeners:
            self.listeners.append(listener)
    def removeEventListener(self, listener):
        print("DriveRootContent.removeEventListener()")
        if listener in self.listeners:
            self.listeners.remove(listener)

    # XCallback
    def notify(self, data):
        for listener in self.contentListeners:
            listener.contentEvent(data)

    # XContentCreator
    def queryCreatableContentsInfo(self):
        print("DriveRootContent.queryCreatableContentsInfo():*************************")
        return self.CreatableContentsInfo
    def createNewContent(self, contentinfo):
        print("DriveRootContent.createNewContent():************************* %s" % self._NewTitle)
        return createNewContent(self.ctx, self.Statement, self.Identifier.getContentIdentifier(), contentinfo, self._NewTitle)

    # XContent
    def getIdentifier(self):
        print("DriveRootContent.getIdentifier()")
        return self.Identifier
    def getContentType(self):
        print("DriveRootContent.getContentType()")
        return self.ContentType
    def addContentEventListener(self, listener):
        print("DriveRootContent.addContentEventListener()")
        self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        print("DriveRootContent.removeContentEventListener()")
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)

    # XCommandProcessor2
    def createCommandIdentifier(self):
        print("DriveRootContent.createCommandIdentifier(): **********************")
        return 0
    def execute(self, command, id, environment):
        print("DriveRootContent.execute(): %s" % command.Name)
        if command.Name == 'getCommandInfo':
            return CommandInfo(self._commandInfo)
        elif command.Name == 'getPropertySetInfo':
            return PropertySetInfo(self._propertySetInfo)
        elif command.Name == 'getPropertyValues':
            namedvalues = getPropertiesValues(self, command.Argument, self.Logger)
            return Row(namedvalues)
        elif command.Name == 'setPropertyValues':
            return setPropertiesValues(self, command.Argument, self.Logger)
        elif command.Name == 'open':
            connection = self.Statement.getConnection()
            mode = self.Identifier.ConnectionMode
            if mode == ONLINE and self.SyncMode == ONLINE:
                print("DriveRootContent.execute(): open 1")
                with getSession(self.ctx, self.Scheme, self.Identifier.UserName) as session:
                    print("DriveRootContent.execute(): open 2")
                    self.SyncMode = updateChildren(connection, session, self.Identifier.UserId, self.Id)
            # Not Used: command.Argument.Properties - Implement me ;-)
            index, select = getChildSelect(connection, mode, self.Id, self.Identifier.getContentIdentifier(), True)
            return DynamicResultSet(self.ctx, self.Scheme, select, index)
        elif command.Name == 'createNewContent':
            print("DriveRootContent.execute(): createNewContent %s" % self._NewTitle)
            return createNewContent(self.ctx, self.Statement, self.Identifier.getContentIdentifier(), command.Argument, self._NewTitle)
        elif command.Name == 'insert':
            print("DriveRootContent.execute() insert")
        elif command.Name == 'delete':
            print("DriveRootContent.execute(): delete")
        elif command.Name == 'transfer':
            # Transfer command is only used for existing document (File Save)
            id = command.Argument.NewTitle
            source = command.Argument.SourceURL
            #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
            #mri.inspect(command.Argument)
            print("DriveRootContent.execute(): transfer: %s - %s" % (source, id))
            if not isChild(self.Statement.getConnection(), id, self.Id):
                # For new document (File Save As) we use command: createNewContent and Insert
                self._NewTitle = id
                print("DriveRootContent.execute(): transfer copy: %s - %s" % (source, id))
                raise InteractiveBadTransferURLException("Couln't handle Url: %s" % source, self)
            print("DriveRootContent.execute(): transfer: %s - %s" % (source, id))
            sf = getSimpleFile(self.ctx)
            if sf.exists(source):
                print("DriveRootContent.execute(): transfer: 1")
                target = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, id))
                stream = sf.openFileRead(source)
                sf.writeFile(target, stream)
                stream.closeInput()
                print("DriveRootContent.execute(): transfer: 2")
                ucb = getUcb(self.ctx)
                print("DriveRootContent.execute(): transfer: 3")
                # Root Uri end whith '/': ie: 'scheme://authority/'
                identifier = ucb.createContentIdentifier('%s%s' % (self.Identifier.getContentIdentifier(), id))
                content = ucb.queryContent(identifier)
                print("DriveRootContent.execute(): transfer: 4")
                size = sf.getSize(target)
                print("DriveRootContent.execute(): transfer: 5")
                updated = {'Size': size}
                if self.Identifier.ConnectionMode == ONLINE:
                    print("DriveRootContent.execute(): transfer: 6")
                    with getSession(self.ctx, self.Scheme, self.Identifier.UserName) as session:
                        print("DriveRootContent.execute(): transfer: 7")
                        stream = sf.openFileRead(target)
                        print("DriveRootContent.execute(): transfer: 8")
                        uploadItem(self.ctx, session, stream, content, size, False)
                else:
                    print("DriveRootContent.execute(): transfer: 9")
                    updated.update({'UpdateMode': 2})
                setContentProperties(content, updated)
                print("DriveRootContent.execute(): transfer: Fin")
                if command.Argument.MoveData:
                    pass #must delete object
        elif command.Name == 'close':
            print("DriveRootContent.execute(): close")
        elif command.Name == 'flush':
            print("DriveRootContent.execute(): flush")
        #except Exception as e:
        #    print("DriveRootContent.execute().Error: %s - %e" % (e, traceback.print_exc()))
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
        properties['ContentType'] = getProperty('ContentType', 'string', bound | readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', bound | readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', bound | readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', bound | readonly)
        properties['Title'] = getProperty('Title', 'string', bound | readonly)
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
            readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
            document = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_DOCUMENT')
            folder = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_FOLDER')
            foldertype = 'application/vnd.google-apps.folder'
            documenttype = 'application/vnd.oasis.opendocument'
            property = (getProperty('Title', 'string', bound), )
            content = (getContentInfo(foldertype, folder, property), getContentInfo(documenttype, document, property))
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
                                        (g_ImplementationName, 'com.sun.star.ucb.Content'))                  # List of implemented services
