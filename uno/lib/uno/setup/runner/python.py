#!
# -*- coding: utf-8 -*-

"""
╔════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                    ║
║   Copyright (c) 2020-25 https://prrvchr.github.io                                  ║
║                                                                                    ║
║   Permission is hereby granted, free of charge, to any person obtaining            ║
║   a copy of this software and associated documentation files (the "Software"),     ║
║   to deal in the Software without restriction, including without limitation        ║
║   the rights to use, copy, modify, merge, publish, distribute, sublicense,         ║
║   and/or sell copies of the Software, and to permit persons to whom the Software   ║
║   is furnished to do so, subject to the following conditions:                      ║
║                                                                                    ║
║   The above copyright notice and this permission notice shall be included in       ║
║   all copies or substantial portions of the Software.                              ║
║                                                                                    ║
║   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,                  ║
║   EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES                  ║
║   OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.        ║
║   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY             ║
║   CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,             ║
║   TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE       ║
║   OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                    ║
║                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════╝
"""

import uno

from .check import Check

from ..helper import getInstalledPackages
from ..helper import getOsLocation
from ..helper import getPackageSimpleData
from ..helper import getPackageVersionData
from ..helper import getRequirementversion
from ..helper import parsePackageName
from ..helper import parsePackageSimpleData
from ..helper import parsePackageVersionData
from ..helper import parseRequirements
from ..helper import getRequirementsUrl
from ..helper import getSetupUpdateMode

from ...unotool import getResourceLocation
from ...unotool import getSimpleFile

from ...configuration import g_identifier

import traceback


class Python(Check):
    def __init__(self, ctx):
        super().__init__(ctx)
        self._packages ={}
        self._data = None
        self._url = None
        self._version = None
        self._success = True
        self.url = getResourceLocation(ctx, g_identifier)
        self._location = getOsLocation(self.url)
        self._requirements = getRequirementsUrl(self.url)
        self.mode = 0
        self.packages = {}
        self.total = 0
        self.label1 = self.resolver.resolveString(311)
        self.label2 = self.resolver.resolveString(312)
        self.steps = self._getCheckStep(ctx)

    def getHeader(self, **kwargs):
        return self.resolver.resolveString(321).format(**kwargs)

    def setReport(self, reports, success):
        return self._getHeader(success), self._getResult(success)

    def callback(self, callback, success=True, error=None):
        callback(success, self._success, error)

    def stepGetInstalledPackages(self, ctx):
        self.mode = getSetupUpdateMode(ctx, g_identifier)
        self._packages = getInstalledPackages(self._location)

    def stepGetStepCount(self):
        self.total += sum(i for i in self._getStepCount())

    def stepGetPackageVersionData(self, requirement, version):
        self._data = getPackageVersionData(requirement, version)

    def stepGetPackageSimpleData(self, requirement):
        self._data = getPackageSimpleData(requirement)

    def stepParsePackageVersionData(self, requirement):
        self._version, self._url = parsePackageVersionData(requirement, self._data)
        self._data = None

    def stepParsePackageSimpleData(self, requirement):
        self._version, self._url = parsePackageSimpleData(requirement, self.mode, self._data)
        self._data = None

    def _getCheckStep(self, ctx):
        if not getSimpleFile(ctx).exists(self._requirements):
            return
        self.total += 2
        yield self._getStepGetInstalledPackages(ctx)
        yield self._getStepGetStepCount()
        for requirement, version1, version2 in self._parsePackages():
            if requirement.url:
                self.packages[requirement.name] = version1, version2, None
                self._success &= version1 == version2
            elif not version1 or version1 != version2:
                if version2:
                    yield self._getStepGetPackageVersionData(requirement, version2)
                    if self._data:
                        yield self._getStepParsePackageVersionData(requirement, version2)
                        if self._version and self._url:
                            self.packages[requirement.name] = version1, self._version, self._url
                            self._version = self._url = None
                            self._success = False
                else:
                    yield self._getStepGetPackageSimpleData(requirement)
                    if self._data:
                        yield self._getStepParsePackageSimpleData(requirement)
                        if self._version and self._url:
                            self.packages[requirement.name] = version1, self._version, self._url
                            self._success &= version1 == self._version
                            self._version = self._url = None
            else:
                self.packages[requirement.name] = version1, version2, None

    def _getStepGetInstalledPackages(self, ctx):
        return 331, (), self.stepGetInstalledPackages, ctx

    def _getStepGetStepCount(self):
        return 341, (), self.stepGetStepCount

    def _getStepGetPackageVersionData(self, requirement, version):
        return 351, (requirement.name, version), self.stepGetPackageVersionData, requirement, version

    def _getStepGetPackageSimpleData(self, requirement):
        return 361, (requirement.name, ), self.stepGetPackageSimpleData, requirement

    def _getStepParsePackageVersionData(self, requirement, version):
        return 371, (requirement.name, version), self.stepParsePackageVersionData, requirement

    def _getStepParsePackageSimpleData(self, requirement):
        return 381, (requirement.name, ), self.stepParsePackageSimpleData, requirement

    def _getStepCount(self):
        for requirement, version1, version2 in self._parsePackages():
            if requirement.url:
                continue
            if not version1 or version1 != version2:
                yield 2

    def _parsePackages(self):
        for requirement in parseRequirements(self._requirements):
            version1 = self._packages.get(parsePackageName(requirement.name))
            version2 = getRequirementversion(requirement, self.mode)
            yield requirement, version1, version2

    def _getHeader(self, success):
        code = 391 if success else 392
        return self.resolver.resolveString(code)

    def _getResult(self, success):
        if success:
            modules = ('%s version %s' % (package, data[1]) for package, data in self.packages.items())
        else:
            modules = ('%s version %s' % (package, data[1]) for package, data in self.packages.items() if data[0] != data[1])
        return ', '.join(modules)

