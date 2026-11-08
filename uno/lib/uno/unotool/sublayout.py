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

from com.sun.star.awt import Size
from com.sun.star.awt.PosSize import POSSIZE

from com.sun.star.awt import WindowEvent

from com.sun.star.awt import XWindowListener


class SubLayout(unohelper.Base,
                XWindowListener):
    def __init__(self, layout, parent=None):
        self._layout = layout
        self._subs = []
        possize = parent.getPosSize() if parent else layout.window.getPosSize()
        self._size = Size(possize.Width, possize.Height)

    def addSubLayout(self, layout):
        possize = layout.window.getPosSize()
        size = Size(possize.Width, possize.Height)
        self._subs.append((layout, size))

    def windowResized(self, event):
        self._layout.windowResized(event)

        possize = event.Source.getPosSize()
        width = possize.Width - self._size.Width
        height = possize.Height - self._size.Height

        for layout, size in self._subs:
            layout.window.setPosSize(0, 0, size.Width + width, size.Height + height, POSSIZE)
            event = WindowEvent()
            event.Source = layout.window
            layout.windowResized(event)

    def windowMoved(self, event):
        pass

    def windowShown(self, event):
        pass

    def windowHidden(self, event):
        pass

    def disposing(self, event):
        pass
