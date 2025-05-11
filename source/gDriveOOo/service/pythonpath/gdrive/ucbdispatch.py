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
import unohelper

from com.sun.star.ui.dialogs.TemplateDescription import FILEOPEN_SIMPLE
from com.sun.star.ui.dialogs.TemplateDescription import FILESAVE_SIMPLE

from com.sun.star.frame import FeatureStateEvent

from com.sun.star.frame import XNotifyingDispatch

from com.sun.star.frame.DispatchResultState import SUCCESS
from com.sun.star.frame.DispatchResultState import FAILURE

from .unotool import createService
from .unotool import getDesktop

import traceback


class UCBDispatch(unohelper.Base,
                  XNotifyingDispatch):
    def __init__(self, ctx, frame):
        self._ctx = ctx
        self._frame = frame
        self._listeners = []
        self._service = 'com.sun.star.ui.dialogs.OfficeFilePicker'
        self._sep = '/'

    _path = ''

# XNotifyingDispatch
    def dispatchWithNotification(self, url, arguments, listener):
        state, result = self.dispatch(url, arguments)
        struct = 'com.sun.star.frame.DispatchResultEvent'
        notification = uno.createUnoStruct(struct, self, state, result)
        listener.dispatchFinished(notification)

    def dispatch(self, url, arguments):
        state = FAILURE
        result = None
        print("UCBDispatch.dispatch() 1")
        if url.Path == 'Open':
            print("UCBDispatch.dispatch() 2")
            fp = createService(self._ctx, self._service, FILEOPEN_SIMPLE)
            print("UCBDispatch.dispatch() 3 Url: %s" % UCBDispatch._path)
            fp.setDisplayDirectory(UCBDispatch._path)
            fp.setMultiSelectionMode(True)
            urls = ()
            if fp.execute():
                print("UCBDispatch.dispatch() 4")
                urls = fp.getSelectedFiles()
                UCBDispatch._path = fp.getDisplayDirectory()
                state = SUCCESS
            fp.dispose()
            if state == SUCCESS:
                desktop = getDesktop(self._ctx)
                for url in urls:
                    print("UCBDispatch.dispatch() 5 URL: %s" % url)
                    desktop.loadComponentFromURL(url, '_default', 0, ())
                    print("UCBDispatch.dispatch() 6 Result: %s" % result)
        elif url.Path == 'SaveAs':
            document = self._frame.getController().getModel()
            source = document.getURL()
            print("UCBDispatch.dispatch() 7 source: %s" % source)
            path, _, name = source.rpartition(self._sep)
            fp = createService(self._ctx, self._service, FILESAVE_SIMPLE)
            print("UCBDispatch.dispatch() 8 path: %s - name: %s" % (path, name))
            fp.setDisplayDirectory(path + self._sep)
            fp.setDefaultName(name)
            if fp.execute():
                target = fp.getSelectedFiles()[0]
                if source != target:
                    print("UCBDispatch.dispatch() 9 target: %s" % target)
                    document.storeAsURL(target, ())
                else:
                    print("UCBDispatch.dispatch() 10 target: %s" % target)
                    document.store()
                state = SUCCESS
                print("UCBDispatch.dispatch() 11 target: %s" % target)
            fp.dispose()
        return state, result

    def addStatusListener(self, listener, url):
        state = FeatureStateEvent()
        state.FeatureURL = url
        state.IsEnabled = True
        #state.State = True
        listener.statusChanged(state)
        self._listeners.append(listener);

    def removeStatusListener(self, listener, url):
        if listener in self._listeners:
            self._listeners.remove(listener)

