#!
# -*- coding: utf_8 -*-

import uno
import unohelper

from com.sun.star.lang import XServiceInfo
from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.ucb import DuplicateProviderException
from com.sun.star.logging.LogLevel import INFO
from com.sun.star.logging.LogLevel import SEVERE

from clouducp import g_identifier
from clouducp import getStringResource
from clouducp import getUcb
from clouducp import getUcp
from clouducp import getLogger
from clouducp import getConfiguration

import traceback

# pythonloader looks for a static g_ImplementationHelper variable
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationName = '%s.OptionsDialog' % g_identifier


class OptionsDialog(unohelper.Base,
                    XServiceInfo,
                    XContainerWindowEventHandler):
    def __init__(self, ctx):
        msg = "OptionsDialog for Plugin: %s loading ... " % g_identifier
        self.ctx = ctx
        self.stringResource = getStringResource(self.ctx, g_identifier, 'CloudUcpOOo', 'OptionsDialog')
        self.Logger = getLogger(self.ctx)
        msg += "Done"
        self.Logger.logp(INFO, 'OptionsDialog', '__init__()', msg)

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
        elif method == 'Changed1':
            self._doChanged1(dialog, event.Source)
            handled = True
        elif method == 'Changed2':
            self._doChanged2(dialog, event.Source)
            handled = True
        elif method == 'LoadUcp':
            self._doLoadUcp(dialog)
            handled = True
        elif method == 'UnloadUcp':
            self._doUnloadUcp(dialog)
            handled = True
        elif method == 'ViewUcp':
            self._doViewUcp(dialog)
            handled = True
        return handled
    def getSupportedMethodNames(self):
        return ('external_event', 'Changed1', 'Changed2', 'LoadUcp', 'UnloadUcp', 'ViewUcp')

    def _initProxy(self):
        self._Proxy = {}
        path = 'org.openoffice.ucb.Configuration'
        config = getConfiguration(self.ctx, path, False)
        paths = ('ContentProviders', 'Local', 'SecondaryKeys', 'Office', 'ProviderData')
        for path in paths:
            config = config.getByName(path)
        for name in config.getElementNames():
            provider = config.getByName(name)
            scheme = provider.getByName('URLTemplate')
            self._Proxy[scheme] = self._registerProxy(provider, scheme)
        #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
        #mri.inspect(ucb)

    def _registerProxy(self, provider, scheme):
        try:
            proxy = {}
            proxy['IsLoaded'] = False
            proxy['IsLoadable'] = False
            proxy['Plugin'] = provider.getByName('Arguments')
            service = provider.getByName('ServiceName')
            print('_initContentProvider(): %s - %s ' % (service, scheme))
            ucp = self.ctx.ServiceManager.createInstanceWithContext(service, self.ctx)
            #if scheme in ('file', 'vnd.google-apps'):
            #    mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
            #    mri.inspect(ucp)
            if ucp.supportsService('com.sun.star.ucb.ContentProviderProxy'):
                proxy['IsLoaded'] = ucp.IsLoaded
                proxy['IsLoadable'] = True
            proxy['Service'] = service
            return proxy
        except Exception as e:
            print('_initContentProvider(): %s - %s - %s' % (service, scheme, e))


    def _loadSetting(self, dialog):
        msg = "OptionsDialog loading setting ... "
        self._initProxy()
        control = dialog.getControl('ListBox1')
        control.Model.StringItemList = self._getProviders()
        self._doChanged1(dialog, control)
        control = dialog.getControl('ListBox2')
        control.Model.StringItemList = self._getProviders(True)
        self._doChanged2(dialog, control)
        msg += "Done"
        self.Logger.logp(INFO, 'OptionsDialog', '_loadSetting()', msg)

    def _saveSetting(self, dialog):
        pass

    def _doLoadUcp(self, dialog):
        control = dialog.getControl('ListBox1')
        scheme = control.SelectedItem
        service = self._Proxy[scheme]['Service']
        ucp = self.ctx.ServiceManager.createInstanceWithContext(service, self.ctx)
        provider = ucp.getContentProvider()
        self._initProxy()
        control.Model.StringItemList = self._getProviders()
        self._doChanged1(dialog, control)
        control = dialog.getControl('ListBox2')
        control.Model.StringItemList = self._getProviders(True)
        self._doChanged2(dialog, control)

    def _doUnloadUcp(self, dialog):
        control = dialog.getControl('ListBox2')
        scheme = control.SelectedItem
        service = self._Proxy[scheme]['Service']
        ucp = self.ctx.ServiceManager.createInstanceWithContext(service, self.ctx)
        provider = ucp.getContentProvider()
        provider.deregisterInstance(scheme, '')
        self._initProxy()
        control.Model.StringItemList = self._getProviders(True)
        self. _doChanged1(dialog, control)
        control = dialog.getControl('ListBox1')
        control.Model.StringItemList = self._getProviders()
        self._doChanged2(dialog, control)

    def _doChanged1(self, dialog, control):
        enabled = control.SelectedItemPos != -1
        enabled = enabled and self._Proxy[control.SelectedItem]['IsLoadable']
        enabled = enabled and not self._Proxy[control.SelectedItem]['IsLoaded']
        dialog.getControl('CommandButton1').Model.Enabled = enabled

    def _doChanged2(self, dialog, control):
        enabled = control.SelectedItemPos != -1
        dialog.getControl('CommandButton2').Model.Enabled = enabled
        dialog.getControl('CommandButton3').Model.Enabled = enabled

    def _doViewUcp(self, dialog):
        control = dialog.getControl('ListBox2')
        scheme = control.SelectedItem
        service = "com.sun.star.ui.dialogs.OfficeFilePicker"
        #service = "com.sun.star.svtools.OfficeFilePicker"
        fp = self.ctx.ServiceManager.createInstanceWithContext(service , self.ctx)
        url = '%s:///' % self._Proxy[scheme]
        fp.setDisplayDirectory(url)
        #mri = self.ctx.ServiceManager.createInstance('mytools.Mri')
        #mri.inspect(fp)
        fp.execute()
        self._loadSetting(dialog)

    def _getProviders1(self, loaded=False):
        schemes = []
        proxy = 'com.sun.star.ucb.ContentProviderProxy'
        ucb = getUcb(self.ctx)
        infos = ucb.queryContentProviders()
        for info in infos:
            self.Logger.logp(INFO, 'OptionsDialog', '_getProviders()', '1')
            scheme = info.Scheme
            self.Logger.logp(INFO, 'OptionsDialog', '_getProviders()', '2 %s' % scheme)
            url = '%s://' % scheme
            self.Logger.logp(INFO, 'OptionsDialog', '_getProviders()', '3')
            try:
                provider = info.ContentProvider
            except Exception as e:
                msg = "Error: %s - %s" % (e, traceback.print_exc())
                logger.logp(SEVERE, "OptionsDialog", "_getProviders()", msg)
            self.Logger.logp(INFO, 'OptionsDialog', '_getProviders()', '4')
            # provider can be None...
            if loaded:
                if not provider or provider.supportsService(proxy):
                    continue
            else:
                if provider and not provider.supportsService(proxy):
                    continue
            self.Logger.logp(INFO, 'OptionsDialog', '_getProviders()', scheme)
            schemes.append(scheme)
        return tuple(schemes)

    def _getProviders(self, loaded=False):
        schemes = []
        for scheme, proxy in self._Proxy.items():
            if loaded:
                if not proxy['IsLoaded']:
                    continue
            else:
                if proxy['IsLoaded']:
                    continue
            print("OptionsDialog._getProviders() %s" % scheme)
            schemes.append(scheme)
        return tuple(schemes)

    # XServiceInfo
    def supportsService(self, service):
        return g_ImplementationHelper.supportsService(g_ImplementationName, service)
    def getImplementationName(self):
        return g_ImplementationName
    def getSupportedServiceNames(self):
        return g_ImplementationHelper.getSupportedServiceNames(g_ImplementationName)


g_ImplementationHelper.addImplementation(OptionsDialog,
                                         g_ImplementationName,
                                        (g_ImplementationName,))
