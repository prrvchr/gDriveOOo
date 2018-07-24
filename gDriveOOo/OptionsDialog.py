#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.awt import XContainerWindowEventHandler

import gdrive
import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = 'com.gmail.prrvchr.extensions.gDriveOOo.OptionsDialog'


class OptionsDialog(unohelper.Base, XServiceInfo, XContainerWindowEventHandler):
    def __init__(self, ctx):
        try:
            self.ctx = ctx
            self.stringResource = gdrive.getStringResource(self.ctx, None, 'OptionsDialog')
        except Exception as e:
            print("PyOptionsDialog.__init__().Error: %s - %s" % (e, traceback.print_exc()))

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
                self._loadSetting(dialog)
                handled = True
        elif method == 'Logger':
            self._doLogger(dialog, bool(event.Source.State))
            handled = True
        elif method == 'View':
            self._doView(dialog)
            handled = True
        elif method == 'Connect':
            self._doConnect(dialog)
            handled = True
        return handled
    def getSupportedMethodNames(self):
        return ('external_event', 'Logger', 'View', 'Connect')

    def _doConnect(self, dialog):
        try:
#           vnd.google-apps://prrvchr@gmail.com/0AAtPs2F6BEgRUk9PVA
#           vnd.google-apps://prrvchr@gmail.com/root
#           vnd.google-apps://lesgeantsdusud@gmail.com/15HyYbehzPMCVFnjqcGRIGr5DjrjWzsTI
#           vnd.google-apps://prrvchr@gmail.com/1brCJfoSt8DraCKpInyCj37bK5dkUhozE
            print("PyOptionsDialog._doConnect() 1")
#            mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
            #handler = self.ctx.ServiceManager.createInstance("com.sun.star.sdb.InteractionHandler")
            #db.IsPasswordRequired = True
            #mri.inspect(db)
            #authentication = gdrive.OAuth2Ooo(self.ctx, 'vnd.google-apps', 'prrvchr@gmail.com')
            #url = gdrive.getResourceLocation(self.ctx, 'CachedContent.odb')
            #db = self.ctx.ServiceManager.createInstance("com.sun.star.sdb.DatabaseContext").getByName(url)
            #connection = db.getConnection('', '')
            #statement = connection.prepareStatement('SELECT * FROM "Item1"')
            #scheme = authentication.Scheme
            #user = authentication.UserName
            name = 'com.gmail.prrvchr.extensions.OAuth2OOo.OAuth2Service'
            service = self.ctx.ServiceManager.createInstanceWithContext(name, self.ctx)
            service.ResourceUrl = 'vnd.google-apps'
            service.UserName = 'prrvchr@gmail.com'
            token = service.Token
#            mri.inspect(service)
            print("PyOptionsDialog._doConnect() 2")
        except Exception as e:
            print("PyOptionsDialog._doConnect().Error: %s - %s" % (e, traceback.print_exc()))

    def _loadSetting(self, dialog):
        self._loadLoggerSetting(dialog)

    def _saveSetting(self, dialog):
        self._saveLoggerSetting(dialog)

    def _doLogger(self, dialog, enabled):
        dialog.getControl('Label2').Model.Enabled = enabled
        dialog.getControl('ComboBox1').Model.Enabled = enabled
        dialog.getControl('OptionButton1').Model.Enabled = enabled
        dialog.getControl('OptionButton2').Model.Enabled = enabled
        dialog.getControl('CommandButton1').Model.Enabled = enabled

    def _doView(self, window):
        url = gdrive.getLoggerUrl(self.ctx)
        length, sequence = gdrive.getFileSequence(self.ctx, url)
        text = sequence.value.decode('utf-8')
        url = 'vnd.sun.star.script:gDriveOOo.LogDialog?location=application'
        dialog = gdrive.createService('com.sun.star.awt.DialogProvider', self.ctx).createDialog(url)
        dialog.Title = url
        dialog.getControl('TextField1').Text = text
        dialog.execute()
        dialog.dispose()

    def _loadLoggerSetting(self, dialog):
        enabled, index, handler = gdrive.getLoggerSetting(self.ctx)
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
        gdrive.setLoggerSetting(self.ctx, enabled, index, handler)

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
