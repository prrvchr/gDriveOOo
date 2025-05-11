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

# Provider configuration
g_scheme = 'vnd-google'
g_extension = 'gDriveOOo'
g_identifier = 'io.github.prrvchr.%s' % g_extension

g_provider = 'Google'
g_host = 'www.googleapis.com'
g_version = 'v3'
g_url = 'https://%s/drive/%s' % (g_host, g_version)
g_upload = 'https://%s/upload/drive/%s/files' % (g_host, g_version)

g_userkeys = ('permissionId','emailAddress','displayName')
g_userfields = 'user(%s)' % ','.join(g_userkeys)
g_capabilitykeys = ('canAddChildren','canRename','canEdit','canReadRevisions')
g_itemkeys = ('id','name','createdTime','modifiedTime','mimeType','size','trashed','parents','capabilities')
g_itemfields = '%s(%s)' % (','.join(g_itemkeys), ','.join(g_capabilitykeys))
g_childfields = 'kind,nextPageToken,files(%s)' % g_itemfields

# Data  minimun chunk: 262144 (256Ko) no more uploads if less... (must be a multiple of 64Ko)
g_chunk = 256 * 1024
g_pages = 200
g_IdentifierRange = (10, 50)

g_ucpfolder = 'application/vnd.google-apps.folder'
g_ucplink   = 'application/vnd.google-apps.link'

g_doc_map = {'application/vnd.google-apps.document':     'application/vnd.oasis.opendocument.text',
             'application/vnd.google-apps.spreadsheet':  'application/vnd.oasis.opendocument.spreadsheet',
             'application/vnd.google-apps.presentation': 'application/vnd.oasis.opendocument.presentation',
             'application/vnd.google-apps.drawing':      'application/vnd.oasis.opendocument.graphics'}

# Resource strings files folder
g_resource = 'resource'
# Logging required global variable
g_basename = 'ContentProvider'
g_defaultlog = 'gDriveLog'
g_errorlog = 'gDriveError'
# Logging global variable
g_synclog = 'gDriveSync'

