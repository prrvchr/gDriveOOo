#!
# -*- coding: utf_8 -*-

import requests


class OAuth2Ooo(object):
    def __init__(self, ctx, scheme=None, username=None):
        name = 'com.gmail.prrvchr.extensions.OAuth2OOo.OAuth2Service'
        self.service = ctx.ServiceManager.createInstanceWithContext(name, ctx)
        if scheme is not None:
            self.service.ResourceUrl = scheme
        if username is not None:
            self.service.UserName = username
    
    @property
    def UserName(self):
        return self.service.UserName
    @UserName.setter
    def UserName(self, username):
        self.service.UserName = username
    @property
    def Scheme(self):
        return self.service.ResourceUrl
    @Scheme.setter
    def Scheme(self, url):
        self.service.ResourceUrl = url

    def __call__(self, request):
        request.headers['Authorization'] = 'Bearer %s' % self.service.Token
        return request
