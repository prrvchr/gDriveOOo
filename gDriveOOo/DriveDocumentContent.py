#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.container import XChild
from com.sun.star.lang import XServiceInfo, NoSupportException
from com.sun.star.ucb import XContent, XCommandProcessor2, CommandAbortedException
from com.sun.star.ucb.ConnectionMode import ONLINE, OFFLINE

from gdrive import Initialization, CommandInfo, PropertySetInfo, Row, InputStream
from gdrive import PropertiesChangeNotifier, PropertySetInfoChangeNotifier, CommandInfoChangeNotifier
from gdrive import getDbConnection, parseDateTime, isChild, getChildSelect, getLogger
from gdrive import updateChildren, createService, getSimpleFile, getResourceLocation
from gdrive import getUcb, getCommandInfo, getProperty, getContentInfo
from gdrive import propertyChange, getPropertiesValues, setPropertiesValues, uploadItem
from gdrive import setContentProperties, getSession, updateData

#from gdrive import PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier, PyPropertyContainer, PyDynamicResultSet
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveDocumentContent'


class DriveDocumentContent(unohelper.Base, XServiceInfo, Initialization, XContent, XChild, XCommandProcessor2,
                           PropertiesChangeNotifier, PropertySetInfoChangeNotifier, CommandInfoChangeNotifier):
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
            
            self.typeMaps = {}
            self.typeMaps['application/vnd.google-apps.document'] = 'application/vnd.oasis.opendocument.text'
            self.typeMaps['application/vnd.google-apps.spreadsheet'] = 'application/x-vnd.oasis.opendocument.spreadsheet'
            self.typeMaps['application/vnd.google-apps.presentation'] = 'application/vnd.oasis.opendocument.presentation'
            self.typeMaps['application/vnd.google-apps.drawing'] = 'application/pdf'
            
            self.initialize(namedvalues)
            self.ObjectId = self.Id
            self.CasePreservingURL = ''
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
    def TitleOnServer(self):
        return self.Name
    @property
    def Title(self):
        return self.Id
    @Title.setter
    def Title(self, title):
        propertyChange(self, 'Name', self.Name, title)
        self.Name = title
    @property
    def Size(self):
        return 0
    @Size.setter
    def Size(self, size):
        self._Size = size
    @property
    def SyncMode(self):
        return self._SyncMode
    @SyncMode.setter
    def SyncMode(self, mode):
        print("DriveDocumentContent.SyncMode.setter()1 %s - %s" % (mode, self._SyncMode))
        old = self._SyncMode
        self._SyncMode |= mode
        print("DriveDocumentContent.SyncMode.setter()2 %s - %s" % (mode, self._SyncMode))
        if self._SyncMode != old:
            propertyChange(self, 'SyncMode', old, self._SyncMode)
    @property
    def MediaType(self):
        return self.typeMaps.get(self.MimeType, self.MimeType)

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
        return 0
    def execute(self, command, id, environment):
        print("DriveDocumentContent.execute(): %s" % command.Name)
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
            sink = command.Argument.Sink
            if sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataSink')):
                msg += " ReadOnly mode selected ..."
                self._setInputStream(sink)
            elif not self.IsReadOnly and sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataStreamer')):
                msg += " ReadWrite mode selected ..."
                self._setStream(sink)
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
                size = sf.getSize(target)
                if self.Identifier.ConnectionMode == ONLINE:
                    stream = sf.openFileRead(target)
                    updateData(self.ctx, self, 28, stream, size)
                else:
                    self.SyncMode = 28
                self.addPropertiesChangeListener(('Id', 'SyncMode', 'Name', 'Size'), getUcp(self.ctx))
                self.Id = self.Id
        elif command.Name == 'delete':
            print("DriveDocumentContent.execute(): delete")
        elif command.Name == 'close':
            print("DriveDocumentContent.execute(): close")
        elif command.Name == 'flush':
            print("DriveDocumentContent.execute(): flush")
        msg += " Done"
        self.Logger.logp(level, "DriveOfficeContent", "execute()", msg)
        return result
    def abort(self, id):
        pass
    def releaseCommandIdentifier(self, id):
        pass

    def _setMimeType(self, mimetype):
        for k,v in self.typeMaps.items():
            if v == mimetype:
                self.MimeType = k
                return
        self.MimeType = mimetype

    def _setInputStream(self, sink):
        sf = getSimpleFile(self.ctx)
        url = self._getUrl(sf)
        if url is None:
            raise CommandAbortedException("Error while downloading file: %s" % self.Name, self)
        sink.setInputStream(sf.openFileRead(url))

    def _setStream(self, sink):
        sf = getSimpleFile(self.ctx)
        url = self._getUrl(sf)
        if url is None:
            raise CommandAbortedException("Error while downloading file: %s" % self.Name, self)
        sink.setStream(sf.openFileReadWrite(url))

    def _getUrl(self, sf):
        url = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, self.Id))
        if not self.SyncMode or not sf.exists(url):
            with getSession(self.ctx, self.Identifier.UserName) as session:
                stream = InputStream(session, self.Id, self.Size, self.MediaType)
                try:
                    sf.writeFile(url, stream)
                except:
                    return None
                else:
                    self.SyncMode = 1
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
        commands['close'] = getCommandInfo('close')
        return commands

    def _getPropertySetInfo(self):
        properties = {}
        bound = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.BOUND')
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['Id'] = getProperty('Id', 'string', bound | readonly)
        properties['ContentType'] = getProperty('ContentType', 'string', bound | readonly)
        properties['MimeType'] = getProperty('MimeType', 'string', bound | readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', bound | readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', bound | readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', bound | readonly)
        properties['Title'] = getProperty('Title', 'string', bound | readonly)
        properties['Size'] = getProperty('Size', 'long', bound | readonly)
        properties['DateModified'] = getProperty('DateModified', 'com.sun.star.util.DateTime', bound | readonly)
        properties['DateCreated'] = getProperty('DateCreated', 'com.sun.star.util.DateTime', bound | readonly)
        properties['IsReadOnly'] = getProperty('IsReadOnly', 'boolean', bound | readonly)
        properties['SyncMode'] = getProperty('SyncMode', 'long', bound)
        properties['ObjectId'] = getProperty('ObjectId', 'string', bound | readonly)
        properties['CasePreservingURL'] = getProperty('CasePreservingURL', 'boolean', bound | readonly)

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
