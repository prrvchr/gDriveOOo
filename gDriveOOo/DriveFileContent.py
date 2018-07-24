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
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.GoogleDriveFileContent'


class PyGoogleDriveFileContent(unohelper.Base, XServiceInfo, PyComponent, PyInitialization,
                               PyPropertyContainer, XContent, XCommandProcessor2, XChild,
                               PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier):
    def __init__(self, ctx, *namedvalues):
        try:
            self.ctx = ctx
            self.Scheme = None
            self.UserName = None
            self.ResultSet = None
            self.ItemUpdate = None
            
            self.CreatableContentsInfo = self._getContentsInfo()
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
            print("PyGoogleDriveFileContent.__init__()")
        except Exception as e:
            print("PyGoogleDriveFileContent.__init__().Error: %s - %e" % (e, traceback.print_exc()))

    @property
    def Location(self):
        return self._Location
    @Location.setter
    def Location(self, location):
        print("PyGoogleDriveFileContent.Location.setter()")
        sink = gdrive.PyActiveDataSink(self.auth, location, self.Size, self.MediaType, self.chunk)
        sink.setInputStream(self.TempFile.getInputStream())
        sink.addListener(gdrive.PyStreamListener())
        sink.start()
        self._Location = location

    @property
    def TempFile(self):
        if self._TempFile is None:
            tmp = gdrive.getTempFile(self.ctx)
            source = gdrive.PyActiveDataSource(self.auth, self.FileId, self.Size, self.chunk)
            source.setOutputStream(tmp.getOutputStream())
            source.start()
            self._TempFile = tmp
        return self._TempFile
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
        if not len(self.ParentsId):
            raise NoSupportException('ParentsId is not set', self)
        return gdrive.queryContent(self.ctx, self.Scheme, self.UserName, self.ParentsId[0])
    def setParent(self):
        raise NoSupportException('ParentsId can not be set', self)

    # XContent
    def getIdentifier(self):
        id = self._getColumn('FileId')
        return gdrive.queryContentIdentifier(self.ctx, self.Scheme, self.UserName, id)
    def getContentType(self):
        return self._getColumn('ContentType')
    def addContentEventListener(self, listener):
        print("PyGoogleDriveFileContent.addContentEventListener() %s :*************************" % len(self.contentListeners))
        if listener not in self.contentListeners:
            self.contentListeners.append(listener)
    def removeContentEventListener(self, listener):
        print("PyGoogleDriveFileContent.removeContentEventListener() %s :*************************" % len(self.contentListeners))
        if listener in self.contentListeners:
            self.contentListeners.remove(listener)

    # XCommandProcessor2
    def createCommandIdentifier(self):
        return 0
    def execute(self, command, id, environment):
        try:
            print("PyGoogleDriveFileContent.execute(): %s" % command.Name)
            if command.Name == 'getCommandInfo':
                return gdrive.PyCommandInfo(self.commands)
            elif command.Name == 'getPropertySetInfo':
                return gdrive.PyPropertySetInfo(self.properties)
            elif command.Name == 'getPropertyValues':
                return gdrive.Row(self.ResultSet, command.Argument)
            elif command.Name == 'setPropertyValues':
                result = gdrive.setPropertiesValues(self, command.Argument)
                return result
            elif command.Name == 'open':
                print("PyGoogleDriveFileContent.execute(): open1 %s" % command.Argument.Mode)
                sink = command.Argument.Sink
                print("PyGoogleDriveFileContent.execute(): open2")
                #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
                #mri.inspect(sink)
                if self.IsReadOnly and sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataSink')):
                    print("PyGoogleDriveFileContent.execute(): open3: %s - %s" % ('com.sun.star.io.XActiveDataSink', self.Size))
                    sink.setInputStream(self.TempFile.getInputStream())
                elif not self.IsReadOnly and sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataStreamer')):
                    print("PyGoogleDriveFileContent.execute(): open3: %s" % 'com.sun.star.io.XActiveDataStreamer')
                    sink.setStream(self.TempFile)
                columns = gdrive.getArgumentColumns(command.Argument)
                print("PyGoogleDriveFileContent.execute(): open5 %s" % (columns, ))
                return PyDynamicResultSet(self.ctx, self.UserName, [], columns, True)
            elif command.Name == 'insert':
                print("PyGoogleDriveFileContent.insert():")
            elif command.Name == 'addProperty':
                print("PyGoogleDriveFileContent.addProperty():")
            elif command.Name == 'removeProperty':
                print("PyGoogleDriveFileContent.removeProperty():")
            elif command.Name == 'close':
                print("PyGoogleDriveFileContent.close()")
        except Exception as e:
            print("PyGoogleDriveFileContent.execute().Error: %s - %e" % (e, traceback.print_exc()))
    def abort(self, id):
        pass
    def releaseCommandIdentifier(self, id):
        pass

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
        print("PyGoogleDriveFileContent._getPipe(): 1")
        pump.start()
        #sink.start()
        #source.setOutputStream(temp.getOutputStream())
        #source.start()
        print("PyGoogleDriveFileContent._getPipe(): 2")
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
        commands['createNewContent'] = gdrive.getCommand('createNewContent', 'com.sun.star.ucb.ContentInfo')
        commands['insert'] = gdrive.getCommand('insert', 'com.sun.star.ucb.InsertCommandArgument')
        commands['close'] = gdrive.getCommand('close')
        return commands

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['FileId'] = gdrive.getProperty('FileId', 'string', readonly)
        properties['ParentsId'] = gdrive.getProperty('ParentsId', '[]string', readonly)
        properties['ContentType'] = gdrive.getProperty('ContentType', 'string', readonly)
        properties['MediaType'] = gdrive.getProperty('MediaType', 'string', readonly)
        properties['IsDocument'] = gdrive.getProperty('IsDocument', 'boolean', readonly)
        properties['IsFolder'] = gdrive.getProperty('IsFolder', 'boolean', readonly)
        properties['Title'] = gdrive.getProperty('Title', 'string', transient)
        properties['Size'] = gdrive.getProperty('Size', 'long', readonly)
        properties['DateModified'] = gdrive.getProperty('DateModified', 'com.sun.star.util.DateTime', readonly)
        properties['CreatableContentsInfo'] = gdrive.getProperty('CreatableContentsInfo', '[]com.sun.star.ucb.ContentInfo', readonly)
        properties['IsReadOnly'] = gdrive.getProperty('IsReadOnly', 'boolean', readonly)
        properties['BaseURI'] = gdrive.getProperty('BaseURI', 'string', readonly)
        #properties['Author'] = gdrive.getProperty('Author', 'string', transient)
        #properties['Keywords'] = gdrive.getProperty('Keywords', 'string', transient)
        #properties['Subject'] = gdrive.getProperty('Subject', 'string', transient)
        properties['TitleOnServer'] = gdrive.getProperty('TitleOnServer', 'string', readonly)
        properties['IsVersionable'] = gdrive.getProperty('IsVersionable', 'boolean', readonly)
        properties['CasePreservingURL'] = gdrive.getProperty('CasePreservingURL', 'string', readonly)
        properties['TempFile'] = gdrive.getProperty('TempFile', 'com.sun.star.io.XTempFile', readonly)
#        properties['CmisProperties'] = gdrive.getProperty('CmisProperties', '[]com.sun.star.beans.PropertyValue', readonly)
        return properties

    def _getContentsInfo(self):
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        document = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_DOCUMENT')
        folder = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_FOLDER')
        ctype = 'application/vnd.google-apps.folder'
        properties = (gdrive.getProperty('Title', 'string', transient), )
        content = ()
        return content

    def _getColumn(self, name):  
        column = self._getColumnByName(self.ResultSet.getColumns(), name)
        return None if column is None else column.getString()

    def _getColumnByName(self, columns, name):
        column = None
        if columns.hasByName(name):
            column = columns.getByName(name)
        return column

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(PyGoogleDriveFileContent,                  # UNO object class
                                         g_ImplementationName,                      # Implementation name
                                        (g_ImplementationName,))                    # List of implemented services
