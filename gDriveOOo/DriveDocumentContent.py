#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.awt import XCallback
from com.sun.star.container import XChild
from com.sun.star.lang import XServiceInfo, NoSupportException
from com.sun.star.ucb import XContent, XCommandProcessor2, CommandAbortedException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE

from gdrive import Initialization, CommandInfo, PropertySetInfo, Row, InputStream, PropertyContainer
from gdrive import PropertiesChangeNotifier, PropertySetInfoChangeNotifier, CommandInfoChangeNotifier
from gdrive import getDbConnection, parseDateTime, getChildSelect, getLogger
from gdrive import createService, getSimpleFile, getResourceLocation
from gdrive import getUcb, getCommandInfo, getProperty, getContentInfo
from gdrive import propertyChange, getPropertiesValues, setPropertiesValues, uploadItem
from gdrive import getCommandIdentifier
from gdrive import ACQUIRED, CREATED, RENAMED, REWRITED, TRASHED

import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveDocumentContent'


class DriveDocumentContent(unohelper.Base, XServiceInfo, Initialization, XContent, XChild, XCommandProcessor2, PropertyContainer,
                           PropertiesChangeNotifier, PropertySetInfoChangeNotifier, CommandInfoChangeNotifier, XCallback):
    def __init__(self, ctx, *namedvalues):
        try:
            self.ctx = ctx
            self.Logger = getLogger(self.ctx)
            level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
            msg = "DriveDocumentContent loading ..."
            self.Logger.logp(level, "DriveDocumentContent", "__init__()", msg)
            self.Identifier = None

            self.ContentType = 'application/vnd.google-apps.document'
            self.Name = 'Sans Nom'
            self.IsFolder = False
            self.IsDocument = True
            self.DateCreated = parseDateTime()
            self.DateModified = parseDateTime()
            self.MimeType = 'application/octet-stream'
            self._Size = 0
            self._Trashed = False

            self.CanAddChild = False
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

            self._commandInfo = self._getCommandInfo()
            self._propertySetInfo = self._getPropertySetInfo()
            self.listeners = []
            self.contentListeners = []
            self.propertiesListener = {}
            self.propertyInfoListeners = []
            self.commandInfoListeners = []
            self.commandIdentifier = 0

            self.typeMaps = {}
            self.typeMaps['application/vnd.google-apps.document'] = 'application/vnd.oasis.opendocument.text'
            self.typeMaps['application/vnd.google-apps.spreadsheet'] = 'application/x-vnd.oasis.opendocument.spreadsheet'
            self.typeMaps['application/vnd.google-apps.presentation'] = 'application/vnd.oasis.opendocument.presentation'
            self.typeMaps['application/vnd.google-apps.drawing'] = 'application/pdf'

            self.initialize(namedvalues)

            self.ObjectId = self.Id
            self.CasePreservingURL = self.Identifier.getContentIdentifier() + 'TEST'
            msg = "DriveDocumentContent loading Uri: %s ... Done" % self.Identifier.getContentIdentifier()
            self.Logger.logp(level, "DriveDocumentContent", "__init__()", msg)
            print("DriveDocumentContent.__init__()")
        except Exception as e:
            print("DriveDocumentContent.__init__().Error: %s - %s" % (e, traceback.print_exc()))

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
    def TitleOnServer(self):
        return self.Name
    @property
    def Title(self):
        return self.Name
    @Title.setter
    def Title(self, title):
        propertyChange(self, 'Name', self.Name, title)
        self.Name = title
    @property
    def Size(self):
        return 0
    @Size.setter
    def Size(self, size):
        propertyChange(self, 'Size', 0, size)
    @property
    def Trashed(self):
        return self._Trashed
    @Trashed.setter
    def Trashed(self, trashed):
        propertyChange(self, 'Trashed', self._Trashed, trashed)
    @property
    def MediaType(self):
        return self.typeMaps.get(self.MimeType, self.MimeType)
    @property
    def Loaded(self):
        return self._Loaded
    @Loaded.setter
    def Loaded(self, loaded):
        propertyChange(self, 'Loaded', self._Loaded, loaded)
        self._Loaded = loaded

    # XCallback
    def notify(self, event):
        for listener in self.contentListeners:
            print("DriveDocumentContent.notify() ***********************************************")
            listener.contentEvent(event)

    # XChild
    def getParent(self):
        print("DriveDocumentContent.getParent() ***********************************************")
        identifier = self.Identifier.getParent()
        return getUcb(self.ctx).queryContent(identifier)
    def setParent(self, parent):
        print("DriveDocumentContent.setParent()")
        raise NoSupportException('Parent can not be set', self)

    # XContent
    def getIdentifier(self):
        print("DriveDocumentContent.getIdentifier()")
        return self.Identifier
    def getContentType(self):
        print("DriveDocumentContent.getContentType()")
        return self.ContentType
    def addContentEventListener(self, listener):
        print("DriveDocumentContent.addContentEventListener()")
        self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        print("DriveDocumentContent.removeContentEventListener()")
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)

    # XCommandProcessor2
    def createCommandIdentifier(self):
        print("DriveDocumentContent.createCommandIdentifier(): **********************")
        return getCommandIdentifier(self)
    def execute(self, command, id, environment):
        print("DriveDocumentContent.execute(): %s - %s" % (command.Name, id))
        result = None
        level = uno.getConstantByName("com.sun.star.logging.LogLevel.INFO")
        msg = "Command name: %s ..." % command.Name
        if command.Name == 'getCommandInfo':
            result = CommandInfo(self._commandInfo)
        elif command.Name == 'getPropertySetInfo':
            result = PropertySetInfo(self._propertySetInfo)
        elif command.Name == 'getPropertyValues':
            namedvalues = getPropertiesValues(self, command.Argument, self.Logger)
            result = Row(namedvalues)
        elif command.Name == 'setPropertyValues':
            result = setPropertiesValues(self, command.Argument, self.Logger)
        elif command.Name == 'open':
            print ("DriveDocumentContent.open(): %s" % command.Argument.Mode)
            sf = getSimpleFile(self.ctx)
            url = self._getUrl(sf)
            if url is None:
                raise CommandAbortedException("Error while downloading file: %s" % self.Name, self)
            sink = command.Argument.Sink
            if sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataSink')):
                msg += " ReadOnly mode selected ..."
                sink.setInputStream(sf.openFileRead(url))
            elif not self.IsReadOnly and sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataStreamer')):
                msg += " ReadWrite mode selected ..."
                sink.setStream(sf.openFileReadWrite(url))
        elif command.Name == 'insert':
            # The Insert command is only used to create a new document (File Save As)
            # it saves content from createNewContent from the parent folder
            print("DriveDocumentContent.execute(): insert %s" % command.Argument)
            stream = command.Argument.Data
            replace = command.Argument.ReplaceExisting
            if stream.queryInterface(uno.getTypeByName('com.sun.star.io.XInputStream')):
                sf = getSimpleFile(self.ctx)
                target = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, self.Id))
                sf.writeFile(target, stream)
                self._setMimeType(getMimeType(self.ctx, stream))
                stream.closeInput()
                self.Size = sf.getSize(target)
                self.addPropertiesChangeListener(('Id', 'Name', 'Size', 'Trashed', 'Loaded'), getUcp(self.ctx))
                self.Id = CREATED+REWRITED
        elif command.Name == 'delete':
            print("DriveDocumentContent.execute(): delete")
            self.Trashed = True
        elif command.Name == 'close':
            print("DriveDocumentContent.execute(): close")
        elif command.Name == 'flush':
            print("DriveDocumentContent.execute(): flush")
        msg += " Done"
        self.Logger.logp(level, "DriveOfficeContent", "execute()", msg)
        return result
    def abort(self, id):
        print("DriveDocumentContent.abort(): %s" % id)
    def releaseCommandIdentifier(self, id):
        pass

    def _setMimeType(self, mimetype):
        for k,v in self.typeMaps.items():
            if v == mimetype:
                self.MimeType = k
                return
        self.MimeType = mimetype

    def _getUrl(self, sf):
        url = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, self.Id))
        if self.Loaded == OFFLINE and sf.exists(url):
            return url
        with self.Identifier.User.Session as session:
            try:
                stream = InputStream(session, self.Id, self.Size, self.MediaType)
                sf.writeFile(url, stream)
            except:
                return None
            else:
                self.Loaded = OFFLINE
            finally:
                stream.closeInput()
        return url

    def _getCommandInfo(self):
        commands = {}
        commands['getCommandInfo'] = getCommandInfo('getCommandInfo')
        commands['getPropertySetInfo'] = getCommandInfo('getPropertySetInfo')
        commands['getPropertyValues'] = getCommandInfo('getPropertyValues', '[]com.sun.star.beans.Property')
        commands['setPropertyValues'] = getCommandInfo('setPropertyValues', '[]com.sun.star.beans.PropertyValue')
        commands['open'] = getCommandInfo('open', 'com.sun.star.ucb.OpenCommandArgument2')
        commands['insert'] = getCommandInfo('insert', 'com.sun.star.ucb.InsertCommandArgument')
#        commands['insert'] = getCommandInfo('insert', 'com.sun.star.ucb.InsertCommandArgument2')
        commands['delete'] = getCommandInfo('delete', 'boolean')
        commands['close'] = getCommandInfo('close')
        return commands

    def _getPropertySetInfo(self):
        properties = {}
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        constrained = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.CONSTRAINED')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['Id'] = getProperty('Id', 'string', bound | readonly)
        properties['ContentType'] = getProperty('ContentType', 'string', bound | readonly)
        properties['MimeType'] = getProperty('MimeType', 'string', bound | readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', bound | readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', bound | readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', bound | readonly)
        properties['Title'] = getProperty('Title', 'string', bound | constrained)
        properties['Size'] = getProperty('Size', 'long', bound | readonly)
        properties['DateModified'] = getProperty('DateModified', 'com.sun.star.util.DateTime', bound | readonly)
        properties['DateCreated'] = getProperty('DateCreated', 'com.sun.star.util.DateTime', bound | readonly)
        properties['IsReadOnly'] = getProperty('IsReadOnly', 'boolean', bound | readonly)
        properties['Loaded'] = getProperty('Loaded', 'long', bound)
        properties['ObjectId'] = getProperty('ObjectId', 'string', bound | readonly)
        properties['CasePreservingURL'] = getProperty('CasePreservingURL', 'string', bound | readonly)

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


g_ImplementationHelper.addImplementation(DriveDocumentContent,                                               # UNO object class
                                         g_ImplementationName,                                               # Implementation name
                                        (g_ImplementationName, 'com.sun.star.ucb.Content'))                  # List of implemented services
