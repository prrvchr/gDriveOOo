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

from ...runner import Progress

from ...unotool import getContainerWindow
from ...unotool import getDesktop
from ...unotool import getDialog
from ...unotool import getDialogPosition
from ...unotool import getTopWindow
from ...unotool import getWindowPosition
from ...unotool import setDialogPosition
from ...unotool import setWindowPosition

from ...configuration import g_identifier

import traceback


class SetupView():
    def __init__(self, ctx, parent, handler, listener, name, point, title, header, step=1):
        if parent:
            self._frame = parent
            self._dialog = getDialog(ctx, g_identifier, 'SetupDialog', parent=parent)
            window = self._dialog.getPeer()
        else:
            self._frame = getTopWindow(ctx, name)
            self._dialog = None
            window = self._frame.getContainerWindow()
        self._window = getContainerWindow(ctx, window, handler, g_identifier, 'SetupWindow')
        if parent:
            setDialogPosition(ctx, self._dialog, parent, point)
            self._dialog.Title = title
            self._window.setVisible(True)
        else:
            # XXX: setComponent is needed if we want a StatusIndicator at the bottom
            self._frame.setComponent(self._window, None)
            self._frame.addCloseListener(listener)
            setWindowPosition(ctx, window, self._window, point)
            self._frame.setTitle(title)
            self._window.setVisible(True)
            # FIXME: If the window loads before the desktop, it should not be made visible.
            if getDesktop(ctx).getCurrentFrame() is not None:
                window.setVisible(True)
        self._getPageHeader(step).Text = header

# SetupView getter methods
    def getWindowPosition(self):
        if self._dialog:
            return getDialogPosition(self._dialog, self._frame)
        return getWindowPosition(self._frame.getContainerWindow())

    def getTraceBack(self):
        return self._getErrorText().Text

    def getIndicator(self):
        return Progress(self._getProgressBar().Model, self._getProgressText())

# SetupView setter methods
    def execute(self):
        if self._dialog:
            return self._dialog.execute()
        return 0

    def close(self, runnable):
        if self._dialog:
            self._dialog.endDialog(runnable)
        else:
            self._frame.close(True)

    def dispose(self):
        if self._dialog:
            self._dialog.dispose()

    def setHeader(self, header, enabled=False, step=2):
        self._setStep(header, step)
        self._getNextButton().Model.Enabled = enabled

    def setResult(self, header, text='', enabled=True, step=3):
        self._setStep(header, step)
        self._getResultText().Text = text
        self._getNextButton().Model.Enabled = enabled

    def setError(self, header, trace, enabled=False, step=4):
        self._setStep(header, step)
        self._getErrorText().Text = trace
        self._getNextButton().Model.Enabled = enabled

    def setMaxProgress(self, value):
        model = self._getProgressBar().Model
        model.ProgressValue = 0
        model.ProgressValueMax = value

    def setProgress(self, text, progress):
        # FIXME: To ensure the label is correctly updated, the progress bar must be updated last.
        self._getProgressText().Text = text
        self._getProgressBar().Model.ProgressValue = progress

    def enableButtons(self, enabled):
        self._getCancelButton().Model.Enabled = enabled
        self._getNextButton().Model.Enabled = enabled

# SetupView private methods
    def _setStep(self, header, step):
        self._window.Model.Step = step
        self._getPageHeader(step).Text = header

# SetupView private control methods
    def _getPageHeader(self, step):
        return self._window.getControl('Label%s' % step)

    def _getProgressBar(self):
        return self._window.getControl('ProgressBar1')

    def _getProgressText(self):
        return self._window.getControl('Label5')

    def _getResultText(self):
        return self._window.getControl('Label6')

    def _getErrorText(self):
        return self._window.getControl('TextField1')

    def _getCancelButton(self):
        return self._window.getControl('CommandButton2')

    def _getNextButton(self):
        return self._window.getControl('CommandButton3')

