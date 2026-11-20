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

from com.sun.star.sdbc import SQLException

from .setup import SetupCheck

from .jdbcdriver import g_agent
from .jdbcdriver import g_extension
from .jdbcdriver import g_identifier
from .jdbcdriver import g_java
from .jdbcdriver import g_protocol
from .jdbcdriver import g_script
from .jdbcdriver import g_service
from .jdbcdriver import g_version


def getExtensions():
    return {g_identifier: (g_extension, g_version)}


def isSetupValid(ctx):
    java = g_extension, g_java, g_script
    return SetupCheck.isValid(ctx, java, extensions=getExtensions())


def checkSetup(ctx, source):
    java = g_extension, g_java, g_script
    agent = g_service, g_protocol, g_agent
    state = SetupCheck.getState(ctx, java=java, agent=agent, python=True, extensions=getExtensions())
    if not state.runnable:
        raise SQLException(state.getMessage(ctx), source, '08001', state.code, None)


def getException(logger, source, code, exc, state, resource, *args):
    error = SQLException()
    error.ErrorCode = code
    error.NextException = exc
    error.SQLState = logger.resolveString(state)
    error.Message = logger.resolveString(resource, *args)
    error.Context = source
    return error
