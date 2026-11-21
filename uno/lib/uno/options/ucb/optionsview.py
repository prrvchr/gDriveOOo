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

from com.sun.star.awt import Size

from ..unotool import Layout
from ..unotool import LinkListener
from ..unotool import SubLayout


class OptionsView():
    def __init__(self, ctx, window):
        self._window = window
        self._link = LinkListener(ctx, self._getLabel())
        self._layout = SubLayout(Layout(window, size=Size(279, 290), **self._getLayouts()))
        window.addWindowListener(self._layout)

# OptionsView getter methods
    def getLayout(self):
        return self._layout

    def getFrame(self):
        return self._getFrame()

    def getSetup(self):
        return self._getSetup()

# OptionView setter methods
    def initView(self, label, url):
        self.refreshView(label, url)

    def refreshView(self, label, url):
        self._setLabel(label, url)

# OptionsView private setter methods
    def _getLayouts(self):
        return {'horizontals': self._getHorizontals()}

    def _getHorizontals(self):
        yield self._getFrame()
        yield self._getSetup()
        yield self._getLabel()

    def _setLabel(self, label, url):
        self._getLabel().Model.Label = label
        self._link.setUrl(url)

# OptionsView private control methods
    def _getFrame(self):
        return self._window.getControl('FrameControl1')

    def _getSetup(self):
        return self._window.getControl('FrameControl2')

    def _getLabel(self):
        return self._window.getControl('Label1')
