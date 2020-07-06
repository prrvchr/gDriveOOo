#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.container import XChild
from com.sun.star.lang import NoSupportException
from com.sun.star.ucb import XContentIdentifier
from com.sun.star.ucb import XRestIdentifier

from com.sun.star.ucb import IllegalIdentifierException

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from com.sun.star.beans.PropertyAttribute import BOUND
from com.sun.star.beans.PropertyAttribute import CONSTRAINED
from com.sun.star.beans.PropertyAttribute import READONLY
from com.sun.star.beans.PropertyAttribute import TRANSIENT

from com.sun.star.ucb.ConnectionMode import OFFLINE
from com.sun.star.ucb.ConnectionMode import ONLINE

from unolib import KeyMap
from unolib import createService
from unolib import getUserNameFromHandler
from unolib import getProperty
from unolib import getResourceLocation
from unolib import parseDateTime

from .contenttools import getUri
from .contenttools import getUrl
from .content import Content
from .logger import logMessage

import traceback


class Identifier(unohelper.Base,
                 XContentIdentifier,
                 XRestIdentifier,
                 XChild):
    def __init__(self, ctx, user, uri, contenttype=''):
        msg = "Identifier loading"
        self.ctx = ctx
        self._contenttype = contenttype
        self._error = None
        self._uri = uri
        self.User = user
        self.MetaData = user.DataBase.getIdentifier(user, uri, self.isNew())
        msg += " ... Done"
        print("Identifier.__init__() OK")
        logMessage(self.ctx, INFO, msg, "Identifier", "__init__()")

    @property
    def Id(self):
        return self.MetaData.getDefaultValue('Id', None)
    @property
    def ParentId(self):
        return self.MetaData.getDefaultValue('ParentId', None)
    @property
    def BaseURI(self):
        return self.MetaData.getDefaultValue('BaseURI', None)
    @property
    def Error(self):
        return self.User.Error if self.User.Error is not None else self._error

    def isNew(self):
        return self._contenttype != ''
    def isRoot(self):
        return self.Id == self.User.RootId
    def isValid(self):
        return self.Id is not None

    def getContent(self):
        if not self.isValid:
            raise IllegalIdentifierException(self.Error, self)
        if self.isNew():
            data = self._getNewContent()
        else:
            data = self.User.DataBase.getItem(self.User.Id, self.Id)
            print("Identifier.getContent() %s" % data)
        if data is None:
            msg = "Error: can't retreive Identifier"
            raise IllegalIdentifierException(msg, self)
        content = Content(self.ctx, self, data)
        print("Identifier.getContent() OK")
        return content

    def _getNewContent(self):
        try:
            print("Identifier._getNewContent() 1")
            timestamp = parseDateTime()
            isfolder = self.User.Provider.isFolder(self._contenttype)
            isdocument = self.User.Provider.isDocument(self._contenttype)
            data = KeyMap()
            data.insertValue('Id', self.Id)
            data.insertValue('ObjectId', self.Id)
            data.insertValue('Title', '')
            data.insertValue('TitleOnServer', '')
            data.insertValue('DateCreated', timestamp)
            data.insertValue('DateModified', timestamp)
            data.insertValue('ContentType',self._contenttype)
            mediatype = self._contenttype if isfolder else ''
            data.insertValue('MediaType', mediatype)
            data.insertValue('Size', 0)
            data.insertValue('Trashed', False)
            data.insertValue('IsRoot', self.isRoot())
            data.insertValue('IsFolder', isfolder)
            data.insertValue('IsDocument', isdocument)
            data.insertValue('CanAddChild', isfolder)
            data.insertValue('CanRename', True)
            data.insertValue('IsReadOnly', False)
            data.insertValue('IsVersionable', isdocument)
            data.insertValue('Loaded', True)
            data.insertValue('BaseURI', self.getContentIdentifier())
            print("Identifier._getNewContent() 2 %s - %s" % (self.Id, self.getContentIdentifier()))
            return data
        except Exception as e:
            print("Identifier._getNewContent() ERROR: %s - %s" % (e, traceback.print_exc()))

    def setTitle(self, title):
        # if Title change we need to change Identifier.getContentIdentifier()
        url = self.BaseURI
        if not url.endswith('/'):
            url += '/'
        url += title
        self._uri = getUri(self.ctx, getUrl(self.ctx, url))
        return title

    # XContentIdentifier
    def getContentIdentifier(self):
        uri = self._uri.getUriReference()
        return uri
    def getContentProviderScheme(self):
        return self._uri.getScheme()

    # XChild
    def getParent(self):
        parent = None
        if not self.isRoot():
            uri = getUri(self.ctx, self.BaseURI)
            parent = Identifier(self.ctx, self.User, uri)
        return parent
    def setParent(self, parent):
        raise NoSupportException('Parent can not be set', self)

    # XRestIdentifier
    def createNewIdentifier(self, contenttype):
        print("Identifier.createNewIdentifier() %s" % (contenttype, ))
        identifier = Identifier(self.ctx, self.User, self._uri, contenttype)
        return identifier

    def getDocumentContent(self, sf, content, size):
        size = 0
        url = '%s/%s' % (self.User.Provider.SourceURL, self.Id)
        if content.getValue('Loaded') == OFFLINE and sf.exists(url):
            size = sf.getSize(url)
            return url, size
        stream = self.User.Provider.getDocumentContent(self.User.Request, content)
        if stream:
            try:
                sf.writeFile(url, stream)
            except Exception as e:
                msg = "ERROR: %s - %s" % (e, traceback.print_exc())
                logMessage(self.ctx, SEVERE, msg, "Identifier", "getDocumentContent()")
            else:
                size = sf.getSize(url)
                loaded = self.User.DataBase.updateLoaded(self.User.Id, self.Id, OFFLINE, ONLINE)
                content.insertValue('Loaded', loaded)
            finally:
                stream.closeInput()
        return url, size

    def getFolderContent(self, content):
        select, updated = self.User.DataBase.getFolderContent(self, content, False)
        if updated:
            loaded = self.User.DataBase.updateLoaded(self.User.Id, self.Id, OFFLINE, ONLINE)
            content.insertValue('Loaded', loaded)
        return select





    def insertNewDocument(self, content):
        parentid = self.getParent().Id
        return self.DataSource.insertNewDocument(self.User.Id, self.Id, parentid, content)

    def insertNewFolder(self, content):
        print("Identifier.insertNewFolder() 1")
        print("Identifier.insertNewFolder() 2 %s" % self.ParentId)
        return self.DataBase.insertNewFolder(self.User.Id, self.Id, self.ParentId, content)

    def countChildTitle(self, title):
        return self.User.DataBase.countChildTitle(self.User.Id, self.Id, title)


    def isChildId(self, title):
        return self.DataSource.isChildId(self.User.Id, self.Id, title)
    def selectChildId(self, title):
        return self._selectChildId(self.Id, title)


    def updateSize(self, itemid, parentid, size):
        print("Identifier.updateSize()*******************")
        return self.User.updateSize(self.DataSource, itemid, parentid, size)
    def updateTrashed(self, value, default):
        parentid = self.getParent().Id
        return self.User.updateTrashed(self.DataSource, self.Id, parentid, value, default)
    def updateTitle(self, value, default):
        parentid = self.getParent().Id
        return self.User.updateTitle(self.DataSource, self.Id, parentid, value, default)

    def getInputStream(self, path, id):
        url = '%s/%s' % (path, id)
        sf = self.ctx.ServiceManager.createInstance('com.sun.star.ucb.SimpleFileAccess')
        if sf.exists(url):
            return sf.getSize(url), sf.openFileRead(url)
        return 0, None

    def _isIdentifier(self, id):
        return self.DataSource.isIdentifier(self.User.Id, id)

    def _selectChildId(self, id, title):
        return self.DataSource.selectChildId(self.User.Id, id, title)

    def _searchId(self, paths, basename):
        # Needed for be able to create a folder in a just created folder...
        id = ''
        paths.append(self.User.RootId)
        for i, path in enumerate(paths):
            if self._isIdentifier(path):
                id = path
                break
        for j in range(i -1, -1, -1):
            id = self._selectChildId(id, paths[j])
        id = self._selectChildId(id, basename)
        return id

    def _getNewMetaData1(self):
        id = self.User.DataBase.getNewIdentifier(self.User)
        data = self.User.DataBase.getIdentifier(self.User.MetaData, self._uri)
        metadata = KeyMap()
        metadata.setValue('Id', id)
        metadata.setValue('ParentId', data.getValue('Id'))
        print("Identifier._getNewMetaData() %s" % (metadata, ))
        return metadata
