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

import unohelper

from com.sun.star.ucb.IOErrorCode import GENERAL

from com.sun.star.task.InteractionClassification import ERROR

from com.sun.star.lang import XServiceInfo

from com.sun.star.ucb import XContent
from com.sun.star.ucb import XCommandProcessor
from com.sun.star.ucb import InteractiveAugmentedIOException
from com.sun.star.ucb import CommandAbortedException
from com.sun.star.ucb import CommandFailedException

from com.sun.star.task import XInteractionAbort
from com.sun.star.task import XInteractionRequest


class ErrorContent(unohelper.Base,
                   XServiceInfo,
                   XContent,
                   XCommandProcessor):

    def __init__(self, ctx, identifier, state):
        self._ctx = ctx
        self._identifier = identifier
        self._state = state
        self._services = ('com.sun.star.ucb.Content',)

    # XContent
    def getIdentifier(self):
        return self._identifier

    def getContentType(self):
        return 'application/vnd.sun.star.error'

    def addContentEventListener(self, _listener):
        pass

    def removeContentEventListener(self, _listener):
        pass

    # XCommandProcessor
    def createCommandIdentifier(self):
        return 1

    def abort(self, _commandId):
        pass

    def execute(self, _command, _commandId, environment):
        message = self._state.getMessage(self._ctx)
        err = InteractiveAugmentedIOException(
            message,
            self,
            ERROR,
            GENERAL,
            ()
        )
        handler = environment.getInteractionHandler() if environment else None
        if handler:
            handler.handle(_SetupInteractionRequest(err))
            raise CommandAbortedException(message, self)
        raise CommandFailedException(message, self, err)

    # XServiceInfo
    def supportsService(self, service):
        return service in self._services

    def getImplementationName(self):
        return 'io.github.prrvchr.ucb.ErrorContent'

    def getSupportedServiceNames(self):
        return self._services


class _SetupInteractionRequest(unohelper.Base,
                               XInteractionRequest):
    def __init__(self, exception):
        self._exception = exception
        self._continuations = (_AbortContinuation(),)

    def getRequest(self):
        return self._exception

    def getContinuations(self):
        return self._continuations


class _AbortContinuation(unohelper.Base,
                         XInteractionAbort):
    def select(self):
        pass
