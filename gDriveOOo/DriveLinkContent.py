#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.ucb import XContent, XCommandProcessor2, IllegalIdentifierException

import gdrive
from gdrive import PyComponent, PyInitialization, PyPropertyContainer
import requests

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.GoogleDriveLinkContent'


class PyGoogleDriveLinkContent(unohelper.Base, XServiceInfo, PyComponent, PyInitialization,
                               PyPropertyContainer, XContent, XCommandProcessor2):
    def __init__(self, ctx, *namedvalues):
        self.ctx = ctx
        self._identifier = None
        if gdrive.getOfficeProductName(self.ctx) == 'OpenOffice':
            requests.packages.urllib3.disable_warnings()
        self.session = requests.Session()
        self.authentication = gdrive.OAuth2Ooo(self.ctx)
        self.ContentType = 'application/vnd.google-apps.file'
        self.IsFolder = False
        self.IsDocument = True
        self.fields = ('id', 'parents', 'name', 'mimeType', 'size', 'modifiedTime')
        self.url ='https://www.googleapis.com/drive/v3/files'
        self.listeners = []
        self.initialize(namedvalues)
        print("PyGoogleDriveLinkContent.__init__()")

    @property
    def Identifier(self):
        return self._identifier
    @Identifier.setter
    def Identifier(self, identifier):
        uri = gdrive.getUri(self.ctx, identifier.getContentIdentifier())
        if not uri.hasAuthority():
            raise IllegalIdentifierException('Identifier has no Authority', self)
        self.authentication.setUri(uri)
        self._identifier = identifier

    # XContent
    def getIdentifier(self):
        return self._identifier
    def getContentType(self):
        return self.ContentType
    def addContentEventListener(self, listener):
        pass
    def removeContentEventListener(self, listener):
        pass

    # XCommandProcessor2
    def createCommandIdentifier(self):
        return 0
    def execute(self, command, id, environment):
        print("PyGoogleDriveLinkContent.execute(): %s" % command.Name)
        if command.Name == 'getCommandInfo':
            commands = self._getCommandInfo()
            return gdrive.PyCommandInfo(commands)
        elif command.Name == 'getPropertySetInfo':
            properties = self._getPropertySetInfo()
            return gdrive.PyPropertySetInfo(properties)
        elif command.Name == 'getPropertyValues':
            values = gdrive.getValuesFromArgument(self, command.Argument)
            return gdrive.PyRow(values)
        elif command.Name == 'setPropertyValues':
            gdrive.setValuesFromArgument(self, command.Argument)
        elif command.Name == 'open':
            sink = command.Argument.Sink
    def abort(self, id):
        pass
    def releaseCommandIdentifier(self, id):
        pass

    def _getCommandInfo(self):
        commands = {}
        commands['getCommandInfo'] = gdrive.getCommand('getCommandInfo')
        commands['getPropertySetInfo'] = gdrive.getCommand('getPropertySetInfo')
        commands['getPropertyValues'] = gdrive.getCommand('getPropertyValues', '[]com.sun.star.beans.Property')
        commands['setPropertyValues'] = gdrive.getCommand('setPropertyValues', '[]com.sun.star.beans.Property')
        commands['open'] = gdrive.getCommand('open', 'com.sun.star.ucb.OpenCommandArgument2')
        return command

    def _getPropertySetInfo(self):
        properties = {}
        readonly = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.READONLY')
        transient = uno.getConstantByName('com.sun.star.beans.PropertyAttribute.TRANSIENT')
        properties['FileId'] = gdrive.getProperty('FileId', 'string', readonly)
        properties['ParentsId'] = gdrive.getProperty('ParentsId', '[]string', readonly)
        properties['ContentType'] = gdrive.getProperty('ContentType', 'string', readonly)
        properties['IsDocument'] = gdrive.getProperty('IsDocument', 'boolean', readonly)
        properties['IsFolder'] = gdrive.getProperty('IsFolder', 'boolean', readonly)
        properties['Title'] = gdrive.getProperty('Title', 'string', transient)
        properties['Size'] = gdrive.getProperty('Size', 'long', readonly)
        return properties

    def _writeBytes(self, sink):
        url = '%s/%s' % (self.url, self.FileId)
        params = {'alt': 'media'}
        timeout = 5
        with self.session.get(url, params=params, timeout=timeout, auth=self.authentication, stream=True) as r:
            if r.status_code == requests.codes.ok:
                with sink as s:
                    for chunk in r.iter_content(1024):
                        s.writeBytes(uno.ByteSequence(chunk))
                    s.flush()
                    s.closeOutput()

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(PyGoogleDriveLinkContent,                  # UNO object class
                                         g_ImplementationName,                      # Implementation name
                                        (g_ImplementationName,))                    # List of implemented services
