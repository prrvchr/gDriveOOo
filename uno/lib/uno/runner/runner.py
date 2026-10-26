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

from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from com.sun.star.awt import XCallback

from .error import CancelException
from .error import RunnerException

from ..unotool import getCallBack

from threading import Timer
import traceback


class Runner(unohelper.Base,
             XCallback):
    def __init__(self, ctx, task, progress, cancel, logger=None):
        self._task = task
        self._total = task.total
        self._progress = progress
        self._cancel = cancel
        self._logger = logger
        self._asyncCall = getCallBack(ctx)

    def start(self):
        if self._progress:
            msg = self._task.getMessage(1)
            self._progress.start(msg, self._task.total)
            if self._logger:
                self._logger.logp(INFO, 'Runner', 'start', msg)
        Timer(self._task.delay, self._call).start()

    def notify(self, data):
        try:
            if self._cancel.isSet():
                raise CancelException()

            if self._task.isExtended(self._total):
                self._total = self._task.total
                if self._progress:
                    msg = self._task.getMessage(2)
                    self._progress.start(msg, self._task.total)
                    self._progress.setValue(self._task.step)
                    if self._logger:
                        self._logger.logp(INFO, 'Runner', 'extended', msg)

            resource, options, call, *args = next(self._task.steps)
            call(*args)
            if self._progress:
                self._task.step += 1
                msg = self._task.resolveString(resource, *options)
                self._progress.setText(msg)
                self._progress.setValue(self._task.step)
                if self._logger:
                    self._logger.logp(INFO, *self._getLogInfos(resource, msg))
            Timer(self._task.delay, self._call).start()

        except StopIteration:
            try:
                if self._progress:
                    self._progress.end()
                    if self._logger:
                        msg = self._task.getMessage(4)
                        self._logger.logp(INFO, 'Runner', 'stop', msg)
                self._task.callback()
            except Exception:
                print("Runner.notify() StopIteration ERROR: %s" % traceback.format_exc())

        except CancelException:
            try:
                self._task.stepFinalize()
                if self._progress:
                    self._progress.end()
                    if self._logger:
                        msg = self._task.getMessage(5)
                        self._logger.logp(SEVERE, 'Runner', 'CancelException', msg)
                self._task.callback(False)
            except Exception:
                print("Runner.notify() CancelException ERROR: %s" % traceback.format_exc())

        except RunnerException as e:
            try:
                self._task.stepFinalize()
                if self._progress:
                    self._progress.end()
                    if self._logger:
                        msg = self._task.getMessage(6, e.cause, e.trace)
                        self._logger.logp(SEVERE, 'Runner', 'RunnerException', msg)
                self._task.callback(False, e)
            except Exception:
                print("Runner.notify() RunnerException ERROR: %s" % e.trace)

        except Exception as e:
            try:
                skipped = self._task.skipSteps()
                if skipped > 0:
                    self._task.step += skipped
                    if self._progress:
                        msg = self._task.getMessage(3)
                        self._progress.setValue(self._task.step)
                        self._progress.setText(msg)
                        if self._logger:
                            self._logger.logp(SEVERE, 'Runner', 'skipSteps', msg)
                    Timer(self._task.delay, self._call).start()
                else:
                    self._task.stepFinalize()
                    trace = traceback.format_exc()
                    if self._progress:
                        self._progress.end()
                        if self._logger:
                            error = e.__class__.__name__
                            msg = self._task.getMessage(6, error, trace)
                            self._logger.logp(SEVERE, 'Runner', 'Exception', msg)
                    self._task.callback(False, RunnerException(e, trace))
            except Exception:
                print("Runner.notify() RunnerException ERROR: %s" % traceback.format_exc())

    def _call(self):
        self._asyncCall.addCallback(self, None)

    def _getLogInfos(self, resource, msg):
        return self._task.getClass(resource), self._task.getMethod(resource), msg

