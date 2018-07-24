#!
# -*- coding: utf_8 -*-

from .oauth2lib import OAuth2Ooo

from .items import getItemInsertStatement, getItemSelectStatement, executeItemInsertStatement
from .google import getItem
from .users import getUserInsertStatement, getUserSelectStatement, executeUserInsertStatement


class Item(object):
    def __init__(self, ctx, scheme, connection):
        self.ctx = ctx
        self.Scheme = scheme
        self.authentication = OAuth2Ooo(self.ctx, scheme)
        self.itemInsert = getItemInsertStatement(connection)
        self.itemSelect = getItemSelectStatement(connection, scheme)
        self.userInsert = getUserInsertStatement(connection)
        self.userSelect = getUserSelectStatement(connection)
        self.RootId = None

    @property
    def UserName(self):
        return self.authentication.UserName
    @UserName.setter
    def UserName(self, username):
        if self.UserName != username:
            self.userSelect.setString(1, username)
            result = self.userSelect.executeQuery()
            if result.next():
                self.authentication.UserName = username
                self.RootId = result.getColumns().getByName('RootId').getString()
            elif self._getRootId(username) is not None:
                self.authentication.UserName = username
                executeUserInsertStatement(self.userInsert, username, self.RootId)

    def get(self, id):
        if id == 'root':
            id = self.RootId
        self.itemSelect.setString(2, id)
        return GetItem(self.authentication, self.itemInsert, self.itemSelect, id)

    def _getRootId(self, username):
        auth = OAuth2Ooo(self.ctx, self.Scheme)
        auth.UserName = username
        json = getItem(auth, 'root')
        if 'id' in json:
            self.RootId = json['id']
        else:
            self.RootId = None
        return self.RootId


class GetItem():
    def __init__(self, authentication, insert, select, id):
        self.authentication = authentication
        self.insert = insert
        self.select = select
        self.id = id

    def execute(self):
        try:
            content = None
            result = self.select.executeQuery()
            if result.next():
                content = result.getColumns().getByName('ContentType').getString()
            else:
                json = getItem(self.authentication, self.id)
                if executeItemInsertStatement(self.insert, json):
                    result = self.select.executeQuery()
                    if result.next():
                        content = result.getColumns().getByName('ContentType').getString()
            return content, self.id
        except Exception as e:
            print("GetItem.execute().Error: %s" % e)

