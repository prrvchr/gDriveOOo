#!
# -*- coding: utf-8 -*-

# Request / OAuth2 configuration
g_oauth2 = 'com.gmail.prrvchr.extensions.OAuth2OOo.OAuth2Service'
g_timeout = (15, 60)

# DataSource configuration
g_protocol = 'jdbc:hsqldb:'
g_path = 'hsqldb'
g_jar = 'hsqldb.jar'
g_class = 'org.hsqldb.jdbcDriver'
g_options = ';default_schema=true;hsqldb.default_table_type=cached;get_column_name=false;ifexists=false'
g_shutdown = ';shutdown=true'
g_csv = '%s.csv;fs=|;ignore_first=true;encoding=UTF-8;quoted=true'

# Provider configuration
g_scheme = 'vnd.google-apps'

g_plugin = 'com.gmail.prrvchr.extensions.gDriveOOo'

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

# Minimun chunk: 262144 (256Ko) no more uploads if less... (must be a multiple of 64Ko (and 32Ko))
g_chunk = 262144
g_buffer = 32768  # InputStream (Downloader) maximum 'Buffers' size
g_pages = 100
g_IdentifierRange = (10, 50)

g_office = 'application/vnd.oasis.opendocument'
g_folder = 'application/vnd.google-apps.folder'
g_link = 'application/vnd.google-apps.drive-sdk'
g_doc_map = {'application/vnd.google-apps.document':     'application/vnd.oasis.opendocument.text',
             'application/vnd.google-apps.spreadsheet':  'application/x-vnd.oasis.opendocument.spreadsheet',
             'application/vnd.google-apps.presentation': 'application/vnd.oasis.opendocument.presentation',
             'application/vnd.google-apps.drawing':      'application/pdf'}
