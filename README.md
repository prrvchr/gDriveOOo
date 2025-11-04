<!--
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
-->
# [![gDriveOOo logo][1]][2] Documentation

**Ce [document][3] en français.**

**The use of this software subjects you to our [Terms Of Use][4] and [Data Protection Policy][5].**

# version [1.4.0][6]

## Introduction:

**gDriveOOo** is part of a [Suite][7] of [LibreOffice][8] ~~and/or [OpenOffice][9]~~ extensions allowing to offer you innovative services in these office suites.

This extension allows you to work in LibreOffice on your files on your phone (files that you have downloaded to your Android phone), even while offline.  
It uses [Google Drive API][10] to synchronize your remote Google Drive files with the help of a local HsqlDB 2.7.2 database.  
This extension is seen by LibreOffice as a [Content Provider][11] responding to the URL: `vnd-google://*`.

Being free software I encourage you:
- To duplicate its [source code][12].
- To make changes, corrections, improvements.
- To open [issue][13] if needed.
- To [participate in the costs][14] of [CASA certification][15].

In short, to participate in the development of this extension.
Because it is together that we can make Free Software smarter.

___

## CASA certification:

To ensure interoperability with **Google**, the **gDriveOOo** extension uses the **OAuth2OOo** extension which requires [CASA certification][15].  
Until now, this certification was free and carried out by a Google partner.  
The **OAuth2OOo** application obtained its [CASA certification][16] on 11/28/2023.

**Now this certification has become paid and costs $600.**

I never anticipated such costs and I am counting on your contribution to finance this certification.

Thank you for your help. [![Sponsor][17]][14]

___

## Requirement:

The gDriveOOo extension uses the OAuth2OOo extension to work.  
It must therefore meet the [requirement of the OAuth2OOo extension][18].

The gDriveOOo extension uses the jdbcDriverOOo extension to work.  
It must therefore meet the [requirement of the jdbcDriverOOo extension][19].  
Additionally, gDriveOOo requires the jdbcDriverOOo extension to be configured to provide `com.sun.star.sdb` as the API level, which is the default configuration.

___

## Installation:

It seems important that the file was not renamed when it was downloaded.  
If necessary, rename it before installing it.

- [![OAuth2OOo logo][20]][21] Install **[OAuth2OOo.oxt][22]** extension [![Version][23]][22]

    You must first install this extension, if it is not already installed.

- [![jdbcDriverOOo logo][24]][25] Install **[jdbcDriverOOo.oxt][26]** extension [![Version][27]][26]

    You must install this extension, if it is not already installed.

- ![gDriveOOo logo][28] Install **[gDriveOOo.oxt][29]** extension [![Version][30]][29]

Restart LibreOffice after installation.  
**Be careful, restarting LibreOffice may not be enough.**
- **On Windows** to ensure that LibreOffice restarts correctly, use Windows Task Manager to verify that no LibreOffice services are visible after LibreOffice shuts down (and kill it if so).
- **Under Linux or macOS** you can also ensure that LibreOffice restarts correctly, by launching it from a terminal with the command `soffice` and using the key combination `Ctrl + C` if after stopping LibreOffice, the terminal is not active (no command prompt).

___

## Use:

**Open your Google Drive:**

In **File -> Open** enter in the first drop-down list:

- For a named Url: **vnd-google://your_account@gmail.com**

or

- For an unnamed Url (anonymous): **vnd-google:///**

And validate not by the **Open** button but by the **Enter** key.

If you don't give **your_account@gmail.com**, you will be asked for...

Anonymous Urls allow you to remain anonymous (your account does not appear in the Url) while named Urls allow you to access several accounts simultaneously.

After authorizing the [OAuth2OOo][21] application to access your Drive files, your Google Drive should open!!! normally  :wink:

___

## How to customize LibreOffice menus:

In order to be able to keep using system dialog windows for opening and saving files in LibreOffice, it is now possible to create custom menus for the commands: **Open Remote** and **Save Remote**.

In the **Menu** tab of the **Tools -> Customize** window, select **Macros** in **Category** to access the two macros: `OpenRemote` and `SaveRemote` under: **My Macros -> gDriveOOo**.  
You will first need to add the `OpenRemote` macro to one of the menus with the **Scope** set to **LibreOffice**, then you will need to open the applications (Writer, Calc, Draw...) possibly using a new document, and add the `OpenRemote` and `SaveRemote` macros with the **Scope** set to the application you want to add the menus to.

The `OpenRemote` macro supports any type of **Scope**, while the `SaveRemote` macro should only be assigned to application-type scopes because it requires a document to already be open in LibreOffice.  
This only needs to be done once for LibreOffice and each application, and unfortunately I haven't found anything simpler yet.

___

## How to build the extension:

Normally, the extension is created with Eclipse for Java and [LOEclipse][31]. To work around Eclipse, I modified LOEclipse to allow the extension to be created with Apache Ant.  
To create the gDriveOOo extension with the help of Apache Ant, you need to:
- Install the [Java SDK][32] version 8 or higher.
- Install [Apache Ant][33] version 1.10.0 or higher.
- Install [LibreOffice and its SDK][34] version 7.x or higher.
- Clone the [gDriveOOo][35] repository on GitHub into a folder.
- From this folder, move to the directory: `source/gDriveOOo/`
- In this directory, edit the file: `build.properties` so that the `office.install.dir` and `sdk.dir` properties point to the folders where LibreOffice and its SDK were installed, respectively.
- Start the archive creation process using the command: `ant`
- You will find the generated archive in the subfolder: `dist/`

___

## Has been tested with:

* LibreOffice 7.3.7.2 - Lubuntu 22.04 - Python version 3.10.12

* LibreOffice 7.5.4.2(x86) - Windows 10 - Python version 3.8.16 (under Lubuntu 22.04 / VirtualBox 6.1.38)

* LibreOffice 7.4.3.2(x64) - Windows 10(x64) - Python version 3.8.15 (under Lubuntu 22.04 / VirtualBox 6.1.38)

* LibreOffice 24.8.0.3 (x86_64) - Windows 10(x64) - Python version 3.9.19 (under Lubuntu 22.04 / VirtualBox 6.1.38)

* **Does not work with OpenOffice** see [bug 128569][36]. Having no solution, I encourage you to install **LibreOffice**.

I encourage you in case of problem :confused:  
to create an [issue][13]  
I will try to solve it :smile:

___

## Historical:

### What has been done for version 0.0.5:

- Integration and use of the new HsqlDB v2.5.1 system versioning.

- Writing of a new [Replicator][37] interface, launched in the background (python Thread) responsible for:

    - Perform the necessary procedures when creating a new user (initial Pull).

    - Carry out pulls regularly (every ten minutes) in order to synchronize any external changes (Pull all changes).

    - Replicate on demand all changes to the hsqldb 2.5.1 database using system versioning (Push all changes).

- Writing of a new [DataBase][38] interface, responsible for making all calls to the database.

- Setting up a cache on the Identifiers, see method: [_getUser()][39], allowing access to a Content (file or folder) without access to the database for subsequent calls.

- Management of duplicate file/folder names by [SQL Views][40]: Child, Twin, Uri, and Title generating unique names if duplicates names exist.  
Although this functionality is only needed for gDriveOOo, it is implemented globally...

- Many other fix...

### What has been done for version 0.0.6:

- Using new scheme: **vnd-google://** as claimed by [draft-king-vnd-urlscheme-03.txt][41]

- Achievement of handling duplicate file/folder names by SQL views in HsqlDB:
    - A [**Twin**][42] view grouping all the duplicates by parent folder and ordering them by creation date, modification date.
    - A [**Uri**][43] view generating unique indexes for each duplicate.
    - A [**Title**][44] view generating unique names for each duplicate.
    - A recursive view [**Path**][45] to generate a unique path for each file / folder.

- Creation of a [Provider][46] able to respond to the two types of Urls supported (named and anonymous).  
  Regular expressions (regex), declared in the [UCB configuration file][47], are now used by OpenOffice/LibreOffice to send URLs to the appropriate ContentProvider.

- Use of the new UNO struct [DateTimeWithTimezone][48] provided by the extension [jdbcDriverOOo][25] since its version 0.0.4.  
  Although this struct already exists in LibreOffice, its creation was necessary in order to remain compatible with OpenOffice (see [Enhancement Request 128560][49]).

- Modification of the [Replicator][37] interface, in order to allow:
    - To choose the data synchronization order (local first then remote or vice versa).
    - Synchronization of local changes by atomic operations performed in chronological order to fully support offline work.  
    To do this, three SQL procedures [GetPushItems][50], [GetPushProperties][51] and [UpdatePushItems][52] are used for each user who has accessed his files / folders.

- Rewrite of the [options window][53] accessible by: **Tools -> Options -> Internet -> gDriveOOo** in order to allow:
    - Access to the two log files concerning the activities of the UCP and the data replicator.
    - Choice of synchronization order.
    - The modification of the interval between two synchronizations.
    - Access to the underlying HsqlDB 2.7.2 database managing your Google Drive metadata.

- The presence or absence of a trailing slash in the Url is now supported.

- Many other fix...

### What has been done for version 1.0.1:

- Implementation of the management of shared files.

- The name of the shared folder can be defined before any connection in: **Tools -> Options -> Internet -> gDriveOOo -> Handle shared documents in folder:**

- Many other fix...

### What has been done for version 1.0.2:

- The absence or obsolescence of the **OAuth2OOo** and/or **jdbcDriverOOo** extensions necessary for the proper functioning of **gDriveOOo** now displays an error message.

- Many other things...

### What has been done for version 1.0.3:

- Support for version **1.2.0** of the **OAuth2OOo** extension. Previous versions will not work with **OAuth2OOo** extension 1.2.0 or higher.

### What has been done for version 1.0.4:

- Support for version **1.2.1** of the **OAuth2OOo** extension. Previous versions will not work with **OAuth2OOo** extension 1.2.1 or higher.

### What has been done for version 1.0.5:

- Support for version **1.2.3** of the **OAuth2OOo** extension. Fixed [issue #12][54].

### What has been done for version 1.0.6:

- Support for version **1.2.4** of the **OAuth2OOo** extension. Many issues resolved.

### What has been done for version 1.0.7:

- Now use Python dateutil package to convert to UNO DateTime.

### What has been done for version 1.1.0:

- All Python packages necessary for the extension are now recorded in a [requirements.txt][55] file following [PEP 508][56].
- Now if you are not on Windows then the Python packages necessary for the extension can be easily installed with the command:  
  `pip install requirements.txt`
- Modification of the [Requirement][57] section.

### What has been done for version 1.1.1:

- Fixed a regression preventing the creation of new files.
- Integration of a fix to workaround the [issue #159988][58].

### What has been done for version 1.1.2:

- The creation of the database, during the first connection, uses the UNO API offered by the jdbcDriverOOo extension since version 1.3.2. This makes it possible to record all the information necessary for creating the database in 6 text tables which are in fact [6 csv files][59].
- Rewriting the [SQL views][60] necessary for managing duplicates. Now a folder or file's path is calculated by a recursive view that supports duplicates.
- Although the extension supports handling duplicate files and folder, it is no longer possible to create or rename them.
- Installing the extension will disable the option to create a backup copy (ie: .bak file) in LibreOffice. If this option is validated then the extension is no longer capable of saving files.
- The extension will ask you to install the OAuth2OOo and jdbcDriverOOo extensions in versions 1.3.4 and 1.3.2 respectively minimum.
- Many fixes.

### What has been done for version 1.1.3:

- Updated the [Python python-dateutil][61] package to version 2.9.0.post0.
- Updated the [Python ijson][62] package to version 3.3.0.
- Updated the [Python packaging][63] package to version 24.1.
- Updated the [Python setuptools][64] package to version 72.1.0 in order to respond to the [Dependabot security alert][65].
- The extension will ask you to install the OAuth2OOo and jdbcDriverOOo extensions in versions 1.3.6 and 1.4.2 respectively minimum.

### What has been done for version 1.1.4:

- Updated the [Python setuptools][64] package to version 73.0.1.
- The extension will ask you to install the OAuth2OOo and jdbcDriverOOo extensions in versions 1.3.7 and 1.4.5 respectively minimum.
- Changes to extension options that require a restart of LibreOffice will result in a message being displayed.
- Support for LibreOffice version 24.8.x.

### What has been done for version 1.1.5:

- Disabling data replication in the extension options will display an explicit message in the replicator log.
- The extension will ask you to install the OAuth2OOo and jdbcDriverOOo extensions in versions 1.3.8 and 1.4.6 respectively minimum.
- Modification of the extension options accessible via: **Tools -> Options... -> Internet -> gDriveOOo** in order to comply with the new graphic charter.

### What has been done for version 1.1.6:

- In order to meet the request of [issue #16][66], the management of the **Shared with me** folder has been implemented.
- Preparation of the extension to the use of a more restricted scope of rights and not requiring the [Casa tier 2 certification][15] which is now chargeable. Thanks Google...
- Remote modifications of the contents of the files are taken into account by the replicator.
- If necessary, it is possible to request an initial synchronization in the extension options. It is also possible to request the download of all files already viewed that have a local copy.
- The replicator provides more comprehensive logging.
- Shared folders are now recognizable by their icon.
- Many fixes.

### What has been done for version 1.2.0:

- The extension will ask you to install the OAuth2OOo and jdbcDriverOOo extensions in versions 1.4.0 and 1.4.6 respectively minimum.
- It is possible to build the extension archive (ie: the oxt file) with the [Apache Ant][33] utility and the [build.xml][67] script file.
- The extension will refuse to install under OpenOffice regardless of version or LibreOffice other than 7.x or higher.
- Added binaries needed for Python libraries to work on Linux and LibreOffice 24.8 (ie: Python 3.9).
- The ability to not specify the user's account name in the URL is working again.

### What has been done for version 1.2.1:

- Updated the [Python packaging][63] package to version 24.2.
- Updated the [Python setuptools][64] package to version 75.8.0.
- Updated the [Python six][68] package to version 1.17.0.
- Support for Python version 3.13.

### What has been done for version 1.3.0:

- Updated the [Python packaging][63] package to version 25.0.
- Downgrade the [Python setuptools][64] package to version 75.3.2. to ensure support for Python 3.8.
- Passive registration deployment that allows for much faster installation of extensions and differentiation of registered UNO services from those provided by a Java or Python implementation. This passive registration is provided by the [LOEclipse][31] extension via [PR#152][69] and [PR#157][70].
- Modified [LOEclipse][31] to support the new `rdb` file format produced by the `unoidl-write` compilation utility. `idl` files have been updated to support both available compilation tools: idlc and unoidl-write.
- It is now possible to build the oxt file of the gDriveOOo extension only with the help of Apache Ant and a copy of the GitHub repository. The [How to build the extension][71] section has been added to the documentation.
- Implemented [PEP 570][72] in [logging][73] to support unique multiple arguments.
- To ensure the correct creation of the gDriveOOo database, it will be checked that the jdbcDriverOOo extension has `com.sun.star.sdb` as API level.
- Wrote two macros `OpenRemote` and `SaveRemote` to create custom menus and be able to keep the system dialog window for opening and saving files in LibreOffice. To make it easier to create these custom menus, the section [How to customize LibreOffice menus][74] has been added to the documentation.
- Requires the **jdbcDriverOOo extension at least version 1.5.0**.
- Requires the **OAuth2OOo extension at least version 1.5.0**.

### What has been done for version 1.3.1:

- Support for LibreOffice 25.2.x and 25.8.x on Windows 64-bit.
- Requires the **jdbcDriverOOo extension at least version 1.5.4**.
- Requires the **OAuth2OOo extension at least version 1.5.2**.

### What has been done for version 1.4.0:

- If the jdbcDriverOOo extension works without Java instrumentation, a warning message will be displayed in the extension options.
- All modal windows now open correctly in modal mode.
- Requires the **jdbcDriverOOo extension at least version 1.6.1**.
- Requires the **OAuth2OOo extension at least version 1.6.1**.
- Has been tested with LibreOfficeDev 26.2.

### What remains to be done for version 1.4.0:

- Add new language for internationalization...

- Anything welcome...

[1]: </img/drive.svg#collapse>
[2]: <https://prrvchr.github.io/gDriveOOo/>
[3]: <https://prrvchr.github.io/gDriveOOo/README_fr>
[4]: <https://prrvchr.github.io/gDriveOOo/source/gDriveOOo/registration/TermsOfUse_en>
[5]: <https://prrvchr.github.io/gDriveOOo/source/gDriveOOo/registration/PrivacyPolicy_en>
[6]: <https://prrvchr.github.io/gDriveOOo#what-has-been-done-for-version-140>
[7]: <https://prrvchr.github.io/>
[8]: <https://www.libreoffice.org/download/download/>
[9]: <https://www.openoffice.org/download/index.html>
[10]: <https://developers.google.com/drive/api/guides/about-sdk>
[11]: <https://wiki.openoffice.org/wiki/Documentation/DevGuide/UCB/Content_Providers>
[12]: <https://github.com/prrvchr/gDriveOOo>
[13]: <https://github.com/prrvchr/gDriveOOo/issues/new>
[14]: <https://github.com/sponsors/prrvchr>
[15]: <https://appdefensealliance.dev/casa>
[16]: <https://github.com/prrvchr/OAuth2OOo/blob/master/LOV_OAuth2OOo.pdf>
[17]: <https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86#right>
[18]: <https://prrvchr.github.io/OAuth2OOo/#requirement>
[19]: <https://prrvchr.github.io/jdbcDriverOOo/#requirement>
[20]: <https://prrvchr.github.io/OAuth2OOo/img/OAuth2OOo.svg#middle>
[21]: <https://prrvchr.github.io/OAuth2OOo>
[22]: <https://github.com/prrvchr/OAuth2OOo/releases/latest/download/OAuth2OOo.oxt>
[23]: <https://img.shields.io/github/v/tag/prrvchr/OAuth2OOo?label=latest#right>
[24]: <https://prrvchr.github.io/jdbcDriverOOo/img/jdbcDriverOOo.svg#middle>
[25]: <https://prrvchr.github.io/jdbcDriverOOo>
[26]: <https://github.com/prrvchr/jdbcDriverOOo/releases/latest/download/jdbcDriverOOo.oxt>
[27]: <https://img.shields.io/github/v/tag/prrvchr/jdbcDriverOOo?label=latest#right>
[28]: <img/gDriveOOo.svg#middle>
[29]: <https://github.com/prrvchr/gDriveOOo/releases/latest/download/gDriveOOo.oxt>
[30]: <https://img.shields.io/github/downloads/prrvchr/gDriveOOo/latest/total?label=v1.4.0#right>
[31]: <https://github.com/LibreOffice/loeclipse>
[32]: <https://adoptium.net/temurin/releases/?version=8&package=jdk>
[33]: <https://ant.apache.org/manual/install.html>
[34]: <https://downloadarchive.documentfoundation.org/libreoffice/old/7.6.7.2/>
[35]: <https://github.com/prrvchr/gDriveOOo.git>
[36]: <https://bz.apache.org/ooo/show_bug.cgi?id=128569>
[37]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/replicator.py>
[38]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/database.py>
[39]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/datasource.py#L127>
[40]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/dbqueries.py>
[41]: <https://datatracker.ietf.org/doc/html/draft-king-vnd-urlscheme-03>
[42]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/dbqueries.py#L163>
[43]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/dbqueries.py#L173>
[44]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/dbqueries.py#L193>
[45]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/dbqueries.py#L213>
[46]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/ucp/provider.py>
[47]: <https://github.com/prrvchr/gDriveOOo/blob/master/source/gDriveOOo/gDriveOOo.xcu#L42>
[48]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/rdb/idl/io/github/prrvchr/css/util/DateTimeWithTimezone.idl>
[49]: <https://bz.apache.org/ooo/show_bug.cgi?id=128560>
[50]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/dbqueries.py#L512>
[51]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/dbqueries.py#L557>
[52]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/dbqueries.py#L494>
[53]: <https://github.com/prrvchr/gDriveOOo/tree/master/uno/lib/uno/options/ucb>
[54]: <https://github.com/prrvchr/gDriveOOo/issues/12>
[55]: <https://github.com/prrvchr/gDriveOOo/releases/latest/download/requirements.txt>
[56]: <https://peps.python.org/pep-0508/>
[57]: <https://prrvchr.github.io/gDriveOOo/#requirement>
[58]: <https://bugs.documentfoundation.org/show_bug.cgi?id=159988>
[59]: <https://github.com/prrvchr/gDriveOOo/tree/master/uno/lib/uno/ucb/hsqldb>
[60]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/ucb/dbqueries.py#L111>
[61]: <https://pypi.org/project/python-dateutil/>
[62]: <https://pypi.org/project/ijson/>
[63]: <https://pypi.org/project/packaging/>
[64]: <https://pypi.org/project/setuptools/>
[65]: <https://github.com/prrvchr/gDriveOOo/security/dependabot/1>
[66]: <https://github.com/prrvchr/gDriveOOo/issues/16>
[67]: <https://github.com/prrvchr/gDriveOOo/blob/master/source/gDriveOOo/build.xml>
[68]: <https://pypi.org/project/six/>
[69]: <https://github.com/LibreOffice/loeclipse/pull/152>
[70]: <https://github.com/LibreOffice/loeclipse/pull/157>
[71]: <https://prrvchr.github.io/gDriveOOo/#how-to-build-the-extension>
[72]: <https://peps.python.org/pep-0570/>
[73]: <https://github.com/prrvchr/gDriveOOo/blob/master/uno/lib/uno/logger/logwrapper.py#L109>
[74]: <https://prrvchr.github.io/gDriveOOo/#how-to-customize-libreoffice-menus>
