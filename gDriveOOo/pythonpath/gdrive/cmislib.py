#!
# -*- coding: utf_8 -*-

import uno
import unohelper

try:
    from com.sun.star.document import XCmisDocument
except ImportError:
    from .cmistools import XCmisDocument


class CmisDocument(unohelper.Base, XCmisDocument):
    def __init__(self, cmisproperties={}):
        self._CmisProperties = cmisproperties

    @property
    def CmisProperties(self):
        return tuple(self._CmisProperties.values)

    #XCmisDocument
    def checkOut(self):
        print("")
    def cancelCheckOut(self):
        pass
    def checkIn(self, ismajor, comment):
        pass
    def isVersionable(self):
        return True
    def canCheckOut(self):
        return True
    def canCancelCheckOut(self):
        return True
    def canCheckIn (self):
        return True
    def updateCmisProperties(self, cmisproperties):
        for cmisproperty in cmisproperties:
            self._CmisProperties.update({cmisproperty.Id: cmisproperty})
    def getAllVersions(self):
        return ()
