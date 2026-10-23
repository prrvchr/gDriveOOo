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

from com.sun.star.awt import Size
from com.sun.star.awt.PosSize import POS
from com.sun.star.awt.PosSize import SIZE

from com.sun.star.ui.dialogs.WizardButton import NEXT
from com.sun.star.ui.dialogs.WizardButton import PREVIOUS
from com.sun.star.ui.dialogs.WizardButton import FINISH
from com.sun.star.ui.dialogs.WizardButton import CANCEL
from com.sun.star.ui.dialogs.WizardButton import HELP

from com.sun.star.util.MeasureUnit import APPFONT

from ...unotool import getContainerWindow
from ...unotool import getDialog
from ...unotool import getParentWindow
from ...unotool import setWindowPosition
from ...unotool import getTopWindow

from ...configuration import g_identifier

import traceback


class WizardView():
    def __init__(self, ctx, handler, listener, parent, name, title, resize, point):
        self._name = 'Roadmap1'
        if name:
            # XXX: With a name we use a TOP XWindow
            self._frame = getTopWindow(ctx, name)
            window = self._frame.getContainerWindow()
            self._dialog = getContainerWindow(ctx, window, handler, g_identifier, 'WizardTop')
            # XXX: setComponent is needed if we want a StatusIndicator at the bottom
            self._frame.setComponent(self._dialog, None)
            self._frame.addCloseListener(listener)
            setWindowPosition(ctx, window, self._dialog, point, POS)
        else:
            # XXX: Without name we use a MODAL XDialog
            self._frame = None
            parent = getParentWindow(ctx, parent)
            self._dialog = getDialog(ctx, g_identifier, 'Wizard', handler, parent)
        rectangle = uno.createUnoStruct('com.sun.star.awt.Rectangle', 0, 0, 85, 180)
        roadmap = self._getRoadmap(title, rectangle, 0)
        self._buttons = {CANCEL: 1, FINISH: 2, NEXT: 3, PREVIOUS: 4, HELP: 5}
        self._spacer = 5
        if not self.isModal() and not resize:
            window.setVisible(True)
            self._dialog.setVisible(True)

# WizardView getter methods
    def isModal(self):
        return self._frame is None

    def getDialog(self):
        return self._dialog

    def getDialogWindow(self):
        if self.isModal():
            return self._dialog
        return self._frame.getContainerWindow()

    def getRoadmapModel(self):
        return self._getRoadmapControl().Model

# WizardView setter methods
    def addItemListener(self, listener):
        self._getRoadmapControl().addItemListener(listener)

    def execute(self):
        if self.isModal():
            return self._dialog.execute()
        return 0

    def endDialog(self, result):
        if self.isModal():
            self._dialog.endDialog(result)

    def close(self):
        if not self.isModal():
            self._frame.close(True)

    def dispose(self):
        if self.isModal():
            self._dialog.dispose()

    def setDialogTitle(self, title):
        if self.isModal():
            self._dialog.setTitle(title)
        else:
            self._frame.setTitle(title)

    def setDialogSize(self, page):
        button = self._getButton(HELP).Model
        button.PositionY = page.Height + self._spacer
        dialog = self._dialog.Model
        dialog.Height = button.PositionY + button.Height + self._spacer
        dialog.Width = page.PositionX + page.Width
        # We assume all buttons are named appropriately
        for i in (1, 2, 3, 4):
            self._setButtonPosition(i, button.PositionY, dialog.Width)
        if not self.isModal():
            window = self._frame.getContainerWindow()
            size = self._dialog.convertSizeToPixel(Size(dialog.Width, dialog.Height), APPFONT)
            window.setPosSize(0, 0, size.Width, size.Height, SIZE)
            # XXX: Visibility should be done after size adjustment
            window.setVisible(True)
            self._dialog.setVisible(True)

    def enableHelpButton(self, enabled):
        self._getButton(HELP).Model.Enabled = enabled

    def enableButton(self, button, enabled):
        self._getButton(button).Model.Enabled = enabled

    def setDefaultButton(self, button):
        self._getButton(button).Model.DefaultButton = True

    def updateButtonPrevious(self, enabled):
        self._getButton(PREVIOUS).Model.Enabled = enabled

    def updateButtonNext(self, enabled):
        button = self._getButton(NEXT).Model
        button.Enabled = enabled
        if enabled:
            button.DefaultButton = True

    def updateButtonFinish(self, enabled):
        button = self._getButton(FINISH).Model
        button.Enabled = enabled
        if enabled:
            button.DefaultButton = True

# WizardView private methods
    def _getRoadmap(self, title, rectangle, tabindex):
        roadmap = self._getRoadmapModel(title, rectangle, tabindex)
        self._dialog.Model.insertByName(self._name, roadmap)
        return self._dialog.getControl(self._name)

    def _getRoadmapModel(self, title, rectangle, tabindex):
        service = 'com.sun.star.awt.UnoControlRoadmapModel'
        model = self._dialog.Model.createInstance(service)
        model.Name = self._name
        model.Text = title
        model.PositionX = rectangle.X
        model.PositionY = rectangle.Y
        model.Height = rectangle.Height
        model.Width = rectangle.Width
        model.TabIndex = tabindex
        return model

    def _setButtonPosition(self, step, y, width):
        # We assume that all buttons are the same Width
        button = self._getButtonByIndex(step).Model
        button.PositionX = width - step * (button.Width + self._spacer)
        button.PositionY = y

    def _getButton(self, button):
        index = self._buttons.get(button)
        return self._getButtonByIndex(index)

# WizardView private control methods
    def _getRoadmapControl(self):
        return self._dialog.getControl(self._name)

    def _getButtonByIndex(self, index):
        return self._dialog.getControl('CommandButton%s' % index)

