#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContent, XCommandProcessor2, IllegalIdentifierException
from com.sun.star.container import XChild
from com.sun.star.lang import NoSupportException

import gdrive
from gdrive import PyComponent, PyInitialization, PyPropertyContainer, PyDynamicResultSet
from gdrive import PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier
import requests
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveOfficeContent'


class DriveOfficeContent(unohelper.Base, XServiceInfo, PyComponent, PyInitialization,
                         PyPropertyContainer, XContent, XCommandProcessor2, XChild,
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
            #self.cmisProperties = self._getCmisProperties()
            self.Author = 'Pierre Vacher'
            self.Keywords = 'clefs de recherche'
            self.Subject = 'Test de GoogleDriveFileContent'
            #self.CmisProperties = gdrive.PyXCmisDocument(self.cmisProperties)
            
            self._TempFile = None
            self._Location = None
            self.chunk = 262144
            
            self.initialize(namedvalues)
            
            self.ItemSelect = gdrive.getItemSelectStatement(self.Connection, self.Scheme, self.UserName, self.FileId)
            self.ItemUpdate = gdrive.getItemUpdateStatement(self.Connection, self.FileId)
            
            self.uri = gdrive.getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, self.FileId))
            self.authentication = gdrive.OAuth2Ooo(self.ctx, self.Scheme, self.UserName)
            print("DriveOfficeContent.__init__()")
        except Exception as e:
            print("DriveOfficeContent.__init__().Error: %s - %e" % (e, traceback.print_exc()))

    @property
    def Location(self):
        return self._Location
    @Location.setter
    def Location(self, location):
        print("DriveOfficeContent.Location.setter()")
        sink = gdrive.PyActiveDataSink(self.auth, location, self.Size, self.MediaType, self.chunk)
        sink.setInputStream(self.TempFile.getInputStream())
        sink.addListener(gdrive.PyStreamListener())
        sink.start()
        self._Location = location

    @property
    def TempFile(self):
        sf = gdrive.getSimpleFile(self.ctx)
        uri = self._getTmpUri()
        return sf.openFileReadWrite(uri)
    @TempFile.setter
    def TempFile(self, uri):
        tmp = gdrive.getTempFile(self.ctx)
        sf = gdrive.getSimpleFile(self.ctx)
#        pump = gdrive.getPump(self.ctx)
#        pump.setInputStream(sf.openFileRead(uri))
#        pump.setOutputStream(tmp.getOutputStream())
#        pump.addListener(gdrive.PyStreamListener())
#        pump.start()
        sf.writeFile(tmp.Uri, sf.openFileRead(uri))
        self.Size = sf.getSize(tmp.Uri)
        self._TempFile = tmp

    # XChild
    def getParent(self):
        print("DriveOfficeContent.getParent()")
        id = self._getParentId()
        return gdrive.queryContent(self.ctx, self.Scheme, self.UserName, id)
    def setParent(self):
        raise NoSupportException('ParentsId can not be set', self)

    # XContent
    def getIdentifier(self):
        return gdrive.queryContentIdentifier(self.ctx, self.Scheme, self.UserName, self.FileId)
    def getContentType(self):
        return 'application/vnd.oasis.opendocument'
    def addContentEventListener(self, listener):
        if listener not in self.contentListeners:
            self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)
        if not len(self.contentListeners):
            print("DriveOfficeContent.removeContentEventListener() %s :*************************" % len(self.contentListeners))

    # XCommandProcessor2
    def createCommandIdentifier(self):
        return 0
    def execute(self, command, id, environment):
        try:
            print("DriveOfficeContent.execute(): %s" % command.Name)
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
                self._setItem(arguments)
                return result
            elif command.Name == 'open':
                print ("DriveOfficeContent.insert(): %s" % command.Argument.Mode)
                sink = command.Argument.Sink
                readonly = self._getIsReadOnly()
                if readonly and sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataSink')):
                    sink.setInputStream(self._getInputStream())
                elif not readonly and sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataStreamer')):
                    sink.setStream(self._getStream())
                return None
            elif command.Name == 'insert':
                print("DriveOfficeContent.insert():")
            elif command.Name == 'addProperty':
                print("DriveOfficeContent.addProperty():")
            elif command.Name == 'removeProperty':
                print("DriveOfficeContent.removeProperty():")
            elif command.Name == 'close':
                print("DriveOfficeContent.close()")
        except Exception as e:
            print("DriveOfficeContent.execute().Error: %s - %e" % (e, traceback.print_exc()))
    def abort(self, id):
        pass
    def releaseCommandIdentifier(self, id):
        pass

    def _setItem(self, values={}, id=None):
        id = self.FileId if id is None else id
        return gdrive.updateItem(self.ItemUpdate, self.ItemSelect, id, values)

    def _getParentId(self):
        result = self.ItemSelect.executeQuery()
        result.next()
        return result.getColumns().getByName('ParentId').getString()

    def _getSize(self):
        result = self.ItemSelect.executeQuery()
        result.next()
        return result.getColumns().getByName('Size').getLong()

    def _getIsReadOnly(self):
        result = self.ItemSelect.executeQuery()
        result.next()
        return result.getColumns().getByName('IsReadOnly').getBoolean()

    def _getStream(self):
        sf = gdrive.getSimpleFile(self.ctx)
        if not sf.exists(self.uri):
            sf.writeFile(self.uri, gdrive.InputStream(self.authentication, self.FileId, self._getSize()))
        return sf.openFileReadWrite(self.uri)

    def _getInputStream(self):
        sf = gdrive.getSimpleFile(self.ctx)
        if not sf.exists(self.uri):
            sf.writeFile(self.uri, gdrive.InputStream(self.authentication, self.FileId, self._getSize()))
        return sf.openFileRead(self.uri)

    def _getTempFiles(self, sink):
        tmp = gdrive.getTempFile(self.ctx)
        #source = gdrive.PyRemoteFileReader(self.auth, self.FileId, self.Size, self.chunk)
        #sink = gdrive.PyTempFileWriter(temp, self.chunk)
        #pipe = gdrive.getPipe(self.ctx)
        pump = gdrive.getPump(self.ctx)
        input = gdrive.PyInputStream(self.auth, self.FileId, self.Size)
        #sink.setInputStream(pipe)
        #source.setOutputStream(pipe)
        pump.setInputStream(input)
        pump.setOutputStream(tmp.getOutputStream())
        listener = gdrive.PyStreamListener(sink, tmp)
        pump.addListener(listener)
        print("DriveOfficeContent._getPipe(): 1")
        pump.start()
        #sink.start()
        #source.setOutputStream(temp.getOutputStream())
        #source.start()
        print("DriveOfficeContent._getPipe(): 2")
        return tmp

    def _getCmisProperties(self):
        cmisProperties = {}
        cmisProperties['name'] = gdrive.getCmisProperty('name', 'Title', self.Title, 'string')
        return cmisProperties

    def _getCommandInfo(self):
        commands = {}
        commands['getCommandInfo'] = gdrive.getCommand('getCommandInfo')
        commands['getPropertySetInfo'] = gdrive.getCommand('getPropertySetInfo')
        commands['getPropertyValues'] = gdrive.getCommand('getPropertyValues', '[]com.sun.star.beans.Property')
        commands['setPropertyValues'] = gdrive.getCommand('setPropertyValues', '[]com.sun.star.beans.Property')
        commands['addProperty'] = gdrive.getCommand('addProperty', 'com.sun.star.ucb.PropertyCommandArgument')
        commands['removeProperty'] = gdrive.getCommand('removeProperty', 'string')
        commands['open'] = gdrive.getCommand('open', 'com.sun.star.ucb.OpenCommandArgument2')
#        commands['createNewContent'] = gdrive.getCommand('createNewContent', 'com.sun.star.ucb.ContentInfo')
        commands['insert'] = gdrive.getCommand('insert', 'com.sun.star.ucb.InsertCommandArgument')
        commands['close'] = gdrive.getCommand('close')
        return commands

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['FileId'] = gdrive.getProperty('FileId', 'string', readonly)
#        properties['ParentsId'] = gdrive.getProperty('ParentsId', '[]string', readonly)
        properties['ContentType'] = gdrive.getProperty('ContentType', 'string', readonly)
        properties['MediaType'] = gdrive.getProperty('MediaType', 'string', readonly)
        properties['IsDocument'] = gdrive.getProperty('IsDocument', 'boolean', readonly)
        properties['IsFolder'] = gdrive.getProperty('IsFolder', 'boolean', readonly)
        properties['Title'] = gdrive.getProperty('Title', 'string', transient)
        properties['Size'] = gdrive.getProperty('Size', 'long', readonly)
        properties['DateModified'] = gdrive.getProperty('DateModified', 'com.sun.star.util.DateTime', readonly)
        properties['DateCreated'] = gdrive.getProperty('DateCreated', 'com.sun.star.util.DateTime', readonly)
        properties['IsReadOnly'] = gdrive.getProperty('IsReadOnly', 'boolean', readonly)
        properties['BaseURI'] = gdrive.getProperty('BaseURI', 'string', readonly)
        properties['TargetURL'] = gdrive.getProperty('TargetURL', 'string', readonly)
        properties['TitleOnServer'] = gdrive.getProperty('TitleOnServer', 'string', readonly)
        properties['IsVersionable'] = gdrive.getProperty('IsVersionable', 'boolean', readonly)
        properties['CasePreservingURL'] = gdrive.getProperty('CasePreservingURL', 'string', readonly)
#        properties['CreatableContentsInfo'] = gdrive.getProperty('CreatableContentsInfo', '[]com.sun.star.ucb.ContentInfo', readonly)
#        properties['CmisProperties'] = gdrive.getProperty('CmisProperties', '[]com.sun.star.beans.PropertyValue', readonly)
#        properties['Author'] = gdrive.getProperty('Author', 'string', transient)
#        properties['Keywords'] = gdrive.getProperty('Keywords', 'string', transient)
#        properties['Subject'] = gdrive.getProperty('Subject', 'string', transient)
        return properties

    def getCreatableContentsInfo(self):
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        document = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_DOCUMENT')
        folder = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_FOLDER')
        ctype = 'application/vnd.google-apps.folder'
        properties = (gdrive.getProperty('Title', 'string', transient), )
        content = ()
        return content

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(DriveOfficeContent,                        # UNO object class
                                         g_ImplementationName,                      # Implementation name
                                        (g_ImplementationName,))                    # List of implemented services
