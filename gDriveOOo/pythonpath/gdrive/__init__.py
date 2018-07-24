#!
# -*- coding: utf-8 -*-

from .oauth2lib import OAuth2Ooo
from .item import Item
from .items import getItemSelectStatement, getItemUpdateStatement, updateItem
from .children import getChildSelectStatement, updateChildren
from .contentlib import Row, DynamicResultSet
from .google import ActiveDataSource, InputStream

from .logger import getLogger, getLoggerSetting, setLoggerSetting, getLoggerUrl
from .unotools import getStringResource, getFileSequence, createService





from .unotools import getResourceLocation, getConfiguration, getCurrentLocale
from .unolib import PyComponent, PyInitialization, PyPropertySet, PyCommandInfo
from .unolib import PyPropertySetInfo, PyPropertyContainer, PyInteractionHandler
from .unotools import getSequence, getProperty, getPropertyValue
from .unotools import generateUuid, createMessageBox
from .unotools import getOfficeProductName, getArgumentsFromNamedValues, getNamedValueFromArguments

from .contentlib import PyDynamicResultSet, PyRow, PyStreamListener
#from .contentlib import PyXCmisDocument
from .contentlib import PyPropertiesChangeNotifier, PyPropertySetInfoChangeNotifier, PyCommandInfoChangeNotifier
from .contenttools import queryContentIdentifierString, queryContentIdentifier, queryContent
from .contenttools import getDateTime, parseDateTime, unparseDateTime, getUcb
from .contenttools import getCommand, getContentInfo, getContentEvent, getArgumentColumns
from .contenttools import getPropertiesValues, setPropertiesValues, getContentValues, getUri
from .contenttools import getNewIdentifier, getResultSet, getTempFile, getResultContent
from .contenttools import getPump, getPipe, createIdentifier, getSimpleFile, getUploadLocation

#from .contenttools import getCmisProperty
