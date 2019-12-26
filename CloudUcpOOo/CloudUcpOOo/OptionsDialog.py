#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.awt import XDialogEventHandler

from unolib import getFileSequence
from unolib import getStringResource
from unolib import getResourceLocation

from clouducp import getLoggerUrl
from clouducp import getLoggerSetting
from clouducp import setLoggerSetting
from clouducp import clearLogger
from clouducp import logMessage

from clouducp import g_scheme
from clouducp import g_extension
from clouducp import g_plugin

import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = '%s.OptionsDialog' % g_plugin


class OptionsDialog(unohelper.Base,
                    XServiceInfo,
                    XContainerWindowEventHandler,
                    XDialogEventHandler):
    def __init__(self, ctx):
        try:
            self.ctx = ctx
            self.stringResource = getStringResource(self.ctx, g_plugin, g_extension, 'OptionsDialog')
            print("PyOptionsDialog.__init__() 1")
        except Exception as e:
            print("PyOptionsDialog.__init__().Error: %s - %s" % (e, traceback.print_exc()))

    def __del__(self):
        #self.Connection.close()
        print("PyOptionsDialog.__del__()***********************")

    # XContainerWindowEventHandler, XDialogEventHandler
    def callHandlerMethod(self, dialog, event, method):
        handled = False
        if method == 'external_event':
            if event == 'ok':
                self._saveSetting(dialog)
                handled = True
            elif event == 'back':
                self._loadSetting(dialog)
                handled = True
            elif event == 'initialize':
                self._initialize(dialog)
                handled = True
        elif method == 'Logger':
            enabled = event.Source.State == 1
            self._toggleLogger(dialog, enabled)
            handled = True
        elif method == 'ViewLog':
            self._doViewLog(dialog)
            handled = True
        elif method == 'ClearLog':
            self._doClearLog(dialog)
        elif method == 'LoadUcp':
            self._doLoadUcp(dialog)
            handled = True
        elif method == 'ViewFile':
            self._doViewFile(dialog)
            handled = True
        return handled
    def getSupportedMethodNames(self):
        return ('external_event', 'Logger', 'ViewLog', 'ClearLog', 'LoadUcp', 'ViewFile')

    def _doViewDataBase(self, dialog):
        try:
            path = getResourceLocation(ctx, g_plugin, 'hsqldb')
            url = '%s/%s.odb' % (path, g_scheme)
            desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
            desktop.loadComponentFromURL(url, '_default', 0, ())
            #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
            #mri.inspect(connection)
            print("PyOptionsDialog._doConnect() 2")
        except Exception as e:
            print("PyOptionsDialog._doConnect().Error: %s - %s" % (e, traceback.print_exc()))

    def _doViewFile(self, dialog):
        print("PyOptionsDialog._doViewFile().Error: %s - %s" % (e, traceback.print_exc()))

    def _initialize(self, dialog):
        print("PyOptionsDialog._initialize()")
        provider = getUcp(self.ctx, g_scheme)
        loaded = provider.supportsService('com.sun.star.ucb.ContentProvider')
        print("OptionsDialog._initialize() %s" % loaded)
        self._toogleSync(dialog, loaded)
        self._loadLoggerSetting(dialog)

    def _loadSetting(self, dialog):
        self._loadLoggerSetting(dialog)

    def _saveSetting(self, dialog):
        self._saveLoggerSetting(dialog)

    def _toogleSync(self, dialog, enabled):
        dialog.getControl('CommandButton2').Model.Enabled = not enabled

    def _doLoadUcp(self, dialog):
        try:
            print("PyOptionsDialog._doLoadUcp() 1")
            provider = getUcp(self.ctx, g_scheme)
            if provider.supportsService('com.sun.star.ucb.ContentProviderProxy'):
                #ucp = provider.getContentProvider()
                #ucp = createService('com.gmail.prrvchr.extensions.gDriveOOo.ContentProvider', self.ctx)
                provider = ucp.registerInstance(g_scheme, '', True)
                self._toogleSync(dialog, True)
            print("PyOptionsDialog._doLoadUcp() 2")
            #identifier = getUcb(self.ctx).createContentIdentifier('%s:///' % g_scheme)
        except Exception as e:
            print("PyOptionsDialog._doLoadUcp().Error: %s - %s" % (e, traceback.print_exc()))

    def _toggleLogger(self, dialog, enabled):
        dialog.getControl('Label1').Model.Enabled = enabled
        dialog.getControl('ComboBox1').Model.Enabled = enabled
        dialog.getControl('OptionButton1').Model.Enabled = enabled
        dialog.getControl('OptionButton2').Model.Enabled = enabled
        #dialog.getControl('CommandButton1').Model.Enabled = enabled

    def _doViewLog(self, window):
        dialog = self._getDialog(window, 'LogDialog')
        url = getLoggerUrl(self.ctx)
        dialog.Title = url
        self._setDialogText(dialog, url)
        dialog.execute()
        dialog.dispose()

    def _doClearLog(self, dialog):
        try:
            clearLogger()
            logMessage(self.ctx, INFO, "ClearingLog ... Done", 'OptionsDialog', '_doClearLog()')
            url = getLoggerUrl(self.ctx)
            self._setDialogText(dialog, url)
        except Exception as e:
            msg = "Error: %s - %s" % (e, traceback.print_exc())
            logMessage(self.ctx, SEVERE, msg, "OptionsDialog", "_doClearLog()")

    def _setDialogText(self, dialog, url):
        length, sequence = getFileSequence(self.ctx, url)
        dialog.getControl('TextField1').Text = sequence.value.decode('utf-8')

    def _getDialog(self, window, name):
        url = 'vnd.sun.star.script:%s.%s?location=application' % (g_extension, name)
        service = 'com.sun.star.awt.DialogProvider'
        provider = self.ctx.ServiceManager.createInstanceWithContext(service, self.ctx)
        arguments = getNamedValueSet({'ParentWindow': window.Peer, 'EventHandler': self})
        dialog = provider.createDialogWithArguments(url, arguments)
        return dialog

    def _loadLoggerSetting(self, dialog):
        enabled, index, handler, viewer = getLoggerSetting(self.ctx)
        dialog.getControl('CheckBox1').State = int(enabled)
        self._setLoggerLevel(dialog.getControl('ComboBox1'), index)
        dialog.getControl('OptionButton%s' % handler).State = 1
        self._toggleLogger(dialog, enabled)

    def _setLoggerLevel(self, control, index):
        control.Text = self._getLoggerLevelText(control.Model.Name, index)

    def _getLoggerLevel(self, control):
        name = control.Model.Name
        for index in range(control.ItemCount):
            if self._getLoggerLevelText(name, index) == control.Text:
                break
        return index

    def _getLoggerLevelText(self, name, index):
        text = 'OptionsDialog.%s.StringItemList.%s' % (name, index)
        return self.stringResource.resolveString(text)

    def _saveLoggerSetting(self, dialog):
        enabled = bool(dialog.getControl('CheckBox1').State)
        index = self._getLoggerLevel(dialog.getControl('ComboBox1'))
        handler = dialog.getControl('OptionButton1').State
        setLoggerSetting(self.ctx, enabled, index, handler)

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(OptionsDialog,                             # UNO object class
                                         g_ImplementationName,                      # Implementation name
                                        (g_ImplementationName,))                    # List of implemented services
