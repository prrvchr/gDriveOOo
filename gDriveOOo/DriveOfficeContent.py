#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo, NoSupportException
from com.sun.star.ucb import XContent, XCommandProcessor2, IllegalIdentifierException
from com.sun.star.container import XChild
from com.sun.star.beans import UnknownPropertyException
from com.sun.star.uno import Exception as UnoException


from gdrive import Component, Initialization, PropertiesChangeNotifier, getPropertiesValues
from gdrive import CommandInfo, PropertySetInfo, Row, InputStream, createService
from gdrive import getItemUpdate, getResourceLocation, parseDateTime
from gdrive import queryContent, queryContentIdentifier, getSimpleFile, getCommandInfo, getProperty
from gdrive import propertyChange, setPropertiesValues
#from gdrive import PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier, PyPropertyContainer
import requests
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.DriveOfficeContent'


class DriveOfficeContent(unohelper.Base, XServiceInfo, Component, Initialization, PropertiesChangeNotifier,
                         XContent, XCommandProcessor2, XChild):
#                         PyPropertyContainer, PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier):
    def __init__(self, ctx, *namedvalues):
        try:
            self.ctx = ctx
            self.Scheme = None
            self.UserName = None
            self.Id = None
            self.ParentId = None
            
            self.ContentType = 'application/vnd.oasis.opendocument'
            self.IsFolder = False
            self.IsDocument = True
            self._Title = 'Sans Nom'
            
            self.MediaType = None
            self.Size = 0
            self.DateModified = parseDateTime()
            self.DateCreated = parseDateTime()
            
            self.IsReadOnly = False
            self.BaseURI = None
            self.IsVersionable = False
            
            
            self.listeners = []
            self.contentListeners = []
            #PyPropertiesChangeNotifier listeners
            self.propertiesListener = {}
            #XPropertySetInfoChangeNotifier listeners
            self.propertyInfoListeners = []
            #XCommandInfoChangeNotifier listeners
            self.commandInfoListeners = []
            #self.cmisProperties = self._getCmisProperties()
            self.Author = 'Pierre Vacher'
            self.Keywords = 'clefs de recherche'
            self.Subject = 'Test de GoogleDriveFileContent'
            #self.CmisProperties = gdrive.PyXCmisDocument(self.cmisProperties)
            
            self.initialize(namedvalues)
            
            self.TitleOnServer = self.Id

            #url = getResourceLocation(self.ctx, '%s.odb' % self.Scheme)
            #db = self.ctx.ServiceManager.createInstance("com.sun.star.sdb.DatabaseContext").getByName(url)
            #connection = db.getConnection('', '')
            #query = uno.getConstantByName('com.sun.star.sdb.CommandType.QUERY')
            #self.ItemSelect = connection.prepareCommand('getItem', query)
            #self.itemSelect.setString(1, self.UserName)
            #self.ItemUpdate = getItemUpdateStatement(connection, self.Id)
            
            #self._setParentId()
            print("DriveOfficeContent.__init__()")
        except Exception as e:
            print("DriveOfficeContent.__init__().Error: %s - %e" % (e, traceback.print_exc()))

    @property
    def Title(self):
        return self._Title
    @Title.setter
    def Title(self, title):
        propertyChange(self, 'Title', self._Title, title)
        self._Title = title

     # XChild
    def getParent(self):
        print("DriveOfficeContent.getParent() ***********************************************")
        identifier = '%s://%s/%s' % (self.Scheme, self.UserName, self.ParentId)
        return queryContent(self.ctx, identifier)
    def setParent(self, parent):
        print("DriveOfficeContent.setParent() ***********************************************")
        raise NoSupportException('Parent can not be set', self)

    # XContent
    def getIdentifier(self):
        identifier = '%s://%s/%s' % (self.Scheme, self.UserName, self.Id)
        return queryContentIdentifier(self.ctx, identifier)
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
                return CommandInfo(self._getCommandInfo())
            elif command.Name == 'getPropertySetInfo':
                return PropertySetInfo(self._getPropertySetInfo())
            elif command.Name == 'getPropertyValues':
                namedvalues = getPropertiesValues(self, command.Argument)
                return Row(namedvalues)
            elif command.Name == 'setPropertyValues':
                return setPropertiesValues(self, command.Argument)
            elif command.Name == 'open':
                print ("DriveOfficeContent.open(): %s" % command.Argument.Mode)
                sink = command.Argument.Sink
                if self.IsReadOnly and sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataSink')):
                    sink.setInputStream(self._getStream().getInputStream())
                elif not self.IsReadOnly and sink.queryInterface(uno.getTypeByName('com.sun.star.io.XActiveDataStreamer')):
                    sink.setStream(self._getStream())
                return None
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

    def _getStream(self):
        sf = getSimpleFile(self.ctx)
        uri = getResourceLocation(self.ctx, '%s/%s' % (self.Scheme, self.Id))
        if not sf.exists(uri):
            input = InputStream(self.ctx, self.Scheme, self.UserName, self.Id, self.Size)
            sf.writeFile(uri, input)
            input.closeInput()
        stream = createService('com.sun.star.io.TempFile')
        stream.RemoveFile = False
        input = sf.openFileRead(uri)
        sf.writeFile(stream.Uri, input)
        input.closeInput()
        return stream

    def _getCommandInfo(self):
        commands = {}
        commands['getCommandInfo'] = getCommandInfo('getCommandInfo')
        commands['getPropertySetInfo'] = getCommandInfo('getPropertySetInfo')
        commands['getPropertyValues'] = getCommandInfo('getPropertyValues', '[]com.sun.star.beans.Property')
        commands['setPropertyValues'] = getCommandInfo('setPropertyValues', '[]com.sun.star.beans.Property')
        commands['addProperty'] = getCommandInfo('addProperty', 'com.sun.star.ucb.PropertyCommandArgument')
        commands['removeProperty'] = getCommandInfo('removeProperty', 'string')
        commands['open'] = getCommandInfo('open', 'com.sun.star.ucb.OpenCommandArgument2')
#        commands['createNewContent'] = getCommandInfo('createNewContent', 'com.sun.star.ucb.ContentInfo')
#        commands['insert'] = getCommandInfo('insert', 'com.sun.star.ucb.InsertCommandArgument')
        commands['close'] = getCommandInfo('close')
        return commands

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['Id'] = getProperty('Id', 'string', readonly)
        properties['ContentType'] = getProperty('ContentType', 'string', readonly)
        properties['MediaType'] = getProperty('MediaType', 'string', readonly)
        properties['IsDocument'] = getProperty('IsDocument', 'boolean', readonly)
        properties['IsFolder'] = getProperty('IsFolder', 'boolean', readonly)
        properties['Title'] = getProperty('Title', 'string', transient)
        properties['Size'] = getProperty('Size', 'long', readonly)
        properties['DateModified'] = getProperty('DateModified', 'com.sun.star.util.DateTime', readonly)
        properties['DateCreated'] = getProperty('DateCreated', 'com.sun.star.util.DateTime', readonly)
        properties['IsReadOnly'] = getProperty('IsReadOnly', 'boolean', readonly)
        properties['BaseURI'] = getProperty('BaseURI', 'string', readonly)
        properties['TargetURL'] = getProperty('TargetURL', 'string', readonly)
        properties['TitleOnServer'] = getProperty('TitleOnServer', 'string', readonly)
        properties['IsVersionable'] = getProperty('IsVersionable', 'boolean', readonly)
        properties['CasePreservingURL'] = getProperty('CasePreservingURL', 'string', readonly)
#        properties['CreatableContentsInfo'] = getProperty('CreatableContentsInfo', '[]com.sun.star.ucb.ContentInfo', readonly)
#        properties['CmisProperties'] = getProperty('CmisProperties', '[]com.sun.star.beans.PropertyValue', readonly)
#        properties['Author'] = getProperty('Author', 'string', transient)
#        properties['Keywords'] = getProperty('Keywords', 'string', transient)
#        properties['Subject'] = getProperty('Subject', 'string', transient)
        return properties

    def getCreatableContentsInfo(self):
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        document = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_DOCUMENT')
        folder = uno.getConstantByName('com.sun.star.ucb.ContentInfoAttribute.KIND_FOLDER')
        ctype = 'application/vnd.google-apps.folder'
        properties = (getProperty('Title', 'string', transient), )
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
