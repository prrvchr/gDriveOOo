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

from com.sun.star.awt.PosSize import POS
from com.sun.star.awt.PosSize import POSSIZE

from com.sun.star.awt import Point
from com.sun.star.awt import Rectangle
from com.sun.star.awt import XWindowListener


class Layout(unohelper.Base,
             XWindowListener):
    def __init__(self, window, controls=(), horizontals=(), tops=(), lefts=(), bottoms=()):
        self.window = window
        controls = list(controls)
        horizontals = list(horizontals)
        tops = list(tops)
        lefts = list(lefts)
        bottoms = list(bottoms)
        size = window.getPosSize()

        self._controls = []
        for ctrl in controls:
            possize = ctrl.getPosSize()
            right = size.Width - (possize.X + possize.Width)
            bottom = size.Height - (possize.Y + possize.Height)
            self._controls.append((ctrl, Rectangle(possize.X, possize.Y, right, bottom)))

        self._horizontals = []
        for ctrl in horizontals:
            pos = ctrl.getPosSize()
            right = size.Width - (pos.X + pos.Width)
            self._horizontals.append((ctrl, Rectangle(pos.X, pos.Y, right, pos.Height)))

        self._tops = []
        for ctrl in tops:
            pos = ctrl.getPosSize()
            self._tops.append((ctrl, Point(size.Width - pos.X, pos.Y)))

        self._lefts = []
        for ctrl in lefts:
            pos = ctrl.getPosSize()
            self._lefts.append((ctrl, Point(pos.X, size.Height - pos.Y)))

        self._bottoms = []
        for ctrl in bottoms:
            pos = ctrl.getPosSize()
            self._bottoms.append((ctrl, Point(size.Width - pos.X, size.Height - pos.Y)))

        self._statics = []
        handled = set(controls + horizontals + tops + lefts + bottoms)
        for ctrl in window.getControls():
            if ctrl not in handled:
                pos = ctrl.getPosSize()
                self._statics.append((ctrl, Point(pos.X, pos.Y)))

    def windowResized(self, event):
        size = event.Source.getPosSize()
        W = size.Width
        H = size.Height

        for ctrl, point in self._statics:
            ctrl.setPosSize(point.X, point.Y, 0, 0, POS)

        for ctrl, possize in self._horizontals:
            width = W - possize.X - possize.Width
            if width > 0:
                ctrl.setPosSize(possize.X, possize.Y, width, possize.Height, POSSIZE)

        for ctrl, point in self._tops:
            ctrl.setPosSize(W - point.X, point.Y, 0, 0, POS)

        for ctrl, point in self._lefts:
            ctrl.setPosSize(point.X, H - point.Y, 0, 0, POS)

        for ctrl, point in self._bottoms:
            ctrl.setPosSize(W - point.X, H - point.Y, 0, 0, POS)

        for ctrl, possize in self._controls:
            width = W - possize.X - possize.Width
            height = H - possize.Y - possize.Height
            if width > 0 and height > 0:
                ctrl.setPosSize(possize.X, possize.Y, width, height, POSSIZE)

    def windowMoved(self, event):
        pass

    def windowShown(self, event):
        pass

    def windowHidden(self, event):
        pass

    def disposing(self, event):
        pass
