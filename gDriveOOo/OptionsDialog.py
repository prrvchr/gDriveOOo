#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.ucb import URLAuthenticationRequest

from gdrive import getStringResource, getFileSequence, createService
from gdrive import getLoggerUrl, getLoggerSetting, setLoggerSetting, getLogger
from gdrive import getPropertyValue, registerDataBase, getUcp, needSync

from gdrive import g_scheme, getDbConnection, getItemFromResult, getSession

import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.OptionsDialog'

g_scheme = 'vnd.google-apps'

class OptionsDialog(unohelper.Base, XServiceInfo, XContainerWindowEventHandler):
    def __init__(self, ctx):
        try:
            self.ctx = ctx
            self.stringResource = getStringResource(self.ctx, None, 'OptionsDialog')
            ucp = getUcp(self.ctx)
            if ucp.supportsService('com.sun.star.ucb.ContentProviderProxy'):
                print("PyOptionsDialog.__init__() 1")
                ucp = ucp.getContentProvider()
            self.ucp = ucp
            #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
            #mri.inspect(ucp)
            #self.Connection = getDbConnection(self.ctx, g_scheme, False)
            print("PyOptionsDialog.__init__() 2")
        except Exception as e:
            print("PyOptionsDialog.__init__().Error: %s - %s" % (e, traceback.print_exc()))

    def __del__(self):
        #self.Connection.close()
        print("PyOptionsDialog.__del__()***********************")

    # XContainerWindowEventHandler
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
            self._doLogger(dialog, bool(event.Source.State))
            handled = True
        elif method == 'ViewLog':
            self._doViewLog(dialog)
            handled = True
        elif method == 'ViewDataBase':
            self._doViewDataBase(dialog)
            handled = True
        elif method == 'ViewFile':
            self._doViewFile(dialog)
            handled = True
        return handled
    def getSupportedMethodNames(self):
        return ('external_event', 'Logger', 'ViewLog', 'ViewDataBase', 'ViewFile')

    def _doViewDataBase(self, dialog):
        try:
            print("PyOptionsDialog._doConnect() 1")
            url = registerDataBase(self.ctx, g_scheme)
            desktop = self.ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
            desktop.loadComponentFromURL(url, '_default', 0, ())
            #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
            #mri.inspect(connection)
            print("PyOptionsDialog._doConnect() 2")
        except Exception as e:
            print("PyOptionsDialog._doConnect().Error: %s - %s" % (e, traceback.print_exc()))

    def _doViewFile(self, dialog):
        try:
            user = getUcp(self.ctx).UserName
            doSync(self.ctx, self.Connection, user)
        except Exception as e:
            print("PyOptionsDialog._doViewFile().Error: %s - %s" % (e, traceback.print_exc()))

    def _initialize(self, dialog):
        print("PyOptionsDialog._initialize()")
        user = getUcp(self.ctx).UserName
        self._toogleSync(dialog, needSync(self.Connection) and user is not None)
        self._loadLoggerSetting(dialog)

    def _loadSetting(self, dialog):
        self._loadLoggerSetting(dialog)

    def _saveSetting(self, dialog):
        self._saveLoggerSetting(dialog)

    def _toogleSync(self, dialog, enabled):
        dialog.getControl('CommandButton3').Model.Enabled = enabled

    def _doLogger(self, dialog, enabled):
        dialog.getControl('Label2').Model.Enabled = enabled
        dialog.getControl('ComboBox1').Model.Enabled = enabled
        dialog.getControl('OptionButton1').Model.Enabled = enabled
        dialog.getControl('OptionButton2').Model.Enabled = enabled
        dialog.getControl('CommandButton1').Model.Enabled = enabled

    def _doViewLog(self, window):
        url = getLoggerUrl(self.ctx)
        length, sequence = getFileSequence(self.ctx, url)
        text = sequence.value.decode('utf-8')
        dialog = self._getLogDialog()
        dialog.Title = url
        dialog.getControl('TextField1').Text = text
        dialog.execute()
        dialog.dispose()

    def _getLogDialog(self):
        url = 'vnd.sun.star.script:gDriveOOo.LogDialog?location=application'
        return createService('com.sun.star.awt.DialogProvider', self.ctx).createDialog(url)

    def _loadLoggerSetting(self, dialog):
        enabled, index, handler = getLoggerSetting(self.ctx)
        dialog.getControl('CheckBox1').State = int(enabled)
        self._setLoggerLevel(dialog.getControl('ComboBox1'), index)
        dialog.getControl('OptionButton%s' % handler).State = 1
        self._doLogger(dialog, enabled)

    def _setLoggerLevel(self, control, index):
        name = control.Model.Name
        text = self.stringResource.resolveString('OptionsDialog.%s.StringItemList.%s' % (name, index))
        control.Text = text

    def _getLoggerLevel(self, control):
        name = control.Model.Name
        for index in range(control.ItemCount):
            text = self.stringResource.resolveString('OptionsDialog.%s.StringItemList.%s' % (name, index))
            if text == control.Text:
                break
        return index

    def _saveLoggerSetting(self, dialog):
        enabled = bool(dialog.getControl('CheckBox1').State)
        index = self._getLoggerLevel(dialog.getControl('ComboBox1'))
        handler = dialog.getControl('OptionButton1').State
        setLoggerSetting(self.ctx, enabled, index, handler)
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
