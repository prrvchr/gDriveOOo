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

from .dbtools import getDbConnection, parseDateTime

from .users import getUserSelect, getUserInsert, executeUserInsert

from .items import getItemSelect, executeItemInsert, getItemInsert, getItemUpdate
from .items import executeUpdateInsertItem

from .children import isChildOfItem, updateChildren, getChildSelect, getChildDelete, getChildInsert

from .identifiers import getIdUpdate, getIdSelect, getIdInsert, getNewId


from .contentlib import ContentIdentifier, Row, DynamicResultSet, CommandInfo, CommandInfoChangeNotifier

from .contenttools import getUri, getUriPath, getUcb, getSimpleFile, getContentInfo, getCommandInfo
from .contenttools import getContent, getContentEvent, getUcp, getNewItem, getParentUri
from .contenttools import getId, getContentProperties, getPropertiesValues, setPropertiesValues, propertyChange
from .contenttools import insertContent, updateContent, getCmisProperty, setContentProperties

from .google import InputStream, getItem

from .logger import getLogger, getLoggerSetting, setLoggerSetting, getLoggerUrl

from .unotools import getResourceLocation, createService, getStringResource
from .unotools import getFileSequence, getProperty, getPropertySetInfoChangeEvent

from .unolib import Component, Initialization, InteractionHandler, PropertiesChangeNotifier
from .unolib import PropertySetInfo, PropertySet, PropertySetInfoChangeNotifier
