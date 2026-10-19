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

from .check import Check

from ..helper import checkAgent
from ..helper import getJavaStatus
from ..helper import getJavaVersion

import traceback


class Java(Check):
    def __init__(self, ctx, java, agent=None):
        super().__init__(ctx)
        self._code = 6
        self._minimum = ''
        self._version = ''
        self.total = 1
        self.label1 = self.resolver.resolveString(20101)
        self.label2 = self.resolver.resolveString(20102)
        self.steps = self._getCheckStep(java, agent)

    def getHeader(self, **kwargs):
        return self.resolver.resolveString(20201).format(**kwargs)

    def setReport(self, reports, success):
        if not success:
            reports.append(self._getReport())
        return self._getHeader(), self._getResult()

    def callback(self, callback, success=True, error=None):
        callback(self._getSuccess(success), error)

    def stepCheckJavaStatus(self, extension, version, script):
        self._minimum = version
        self._code = getJavaStatus(self._ctx)

    def stepCheckJavaVersion(self, extension, version, script):
        self._code, self._version = getJavaVersion(self._ctx, True, extension, version, script)

    def stepCheckJavaAgent(self, service, url, agent):
        self._code = checkAgent(self._ctx, service, url, agent)

    def _getCheckStep(self, java, agent):
        yield self._getStepCheckJavaStatus(*java)
        if self._hasJava():
            self.total += 1
            yield self._getStepCheckJavaVersion(*java)
            if self._hasJava() and agent:
                self.total += 1
                yield self._getStepCheckJavaAgent(*agent)

    def _getStepCheckJavaStatus(self, extension, version, script):
        return 20301, (), self.stepCheckJavaStatus, extension, version, script

    def _getStepCheckJavaVersion(self, extension, version, script):
        return 20401, (version, ), self.stepCheckJavaVersion, extension, version, script

    def _getStepCheckJavaAgent(self, service, url, agent):
        return 20501, (), self.stepCheckJavaAgent, service, url, agent

    def _hasJava(self):
        return self._code == 0

    def _noAgent(self):
        return self._code == 1

    def _getHeader(self):
        code = 20601 + self._code
        return self.resolver.resolveString(code).format(version=self._version, minimum=self._minimum)

    def _getReport(self):
        code = 20701 if self._noAgent() else 20702
        return self.resolver.resolveString(code), self._getResult(), False

    def _getResult(self):
        if self._hasJava():
            return 'Java JDK version %s' % self._version
        if self._noAgent():
            return ''
        return 'Java JDK version %s minimum' % self._minimum

    def _getSuccess(self, success):
        return success and self._hasJava()

