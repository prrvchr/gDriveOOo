#!
# -*- coding: utf-8 -*-

#from pkgutil import iter_modules

#from com.sun.star.document import document

#def existModule(module, path):
#    return module in (name for loader, name, ispkg in iter_modules(path))

#exist = existModule('XCmisDocument', document.__path__)
#print("__init__ %s" % exist)

#from .unotools import isCmisReady

from .cmislib import CmisDocument

from .dbtools import getDbConnection, registerDataBase, getItemFromResult

from .items import selectUser, mergeJsonUser, selectItem, insertJsonItem, needSync

from .children import isChildId, selectChildId, getChildSelect

from .identifiers import checkIdentifiers, getNewIdentifier, isIdentifier


from .contentlib import ContentUser, ContentIdentifier, CommandInfo, CommandInfoChangeNotifier
from .contentlib import InteractionRequestParameters, Row, DynamicResultSet, InteractionRequestName
from .contentlib import InteractionRequest, InteractionAbort

from .contenttools import getUcb, getUcp, getUri, getMimeType
from .contenttools import getContentEvent, getCmisProperty, getCommandInfo, getContentInfo
from .contenttools import executeContentCommand, propertyChange, doSync
from .contenttools import uploadItem, getSession, createContent, getIllegalIdentifierException
from .contenttools import getInteractiveNetworkOffLineException, getInteractiveNetworkReadException
from .contenttools import getUnsupportedNameClashException, getInsertCommandArgument

from .contentcore import getCommandIdentifier, updateContent, setPropertiesValues, getPropertiesValues

from .google import InputStream, getUser, getItem, getConnectionMode, updateItem, parseDateTime
from .google import g_scheme, g_folder
from .google import RETRIEVED, CREATED, FOLDER, FILE, RENAMED, REWRITED, TRASHED

from .logger import getLogger, getLoggerSetting, setLoggerSetting, getLoggerUrl

from .unotools import getResourceLocation, createService, getStringResource, getPropertyValue
from .unotools import getFileSequence, getProperty, getPropertySetInfoChangeEvent, getSimpleFile
from .unotools import getInteractionHandler, getPropertyValueSet

from .unolib import Component, Initialization, InteractionHandler, PropertiesChangeNotifier
from .unolib import PropertySetInfo, CmisPropertySetInfo, PropertySet, PropertySetInfoChangeNotifier

from .unocore import PropertyContainer
