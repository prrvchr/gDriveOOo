**The use of this software subjects you to our** [Terms Of Use](https://prrvchr.github.io/gDriveOOo/gDriveOOo/registration/TermsOfUse_en) **and** [Data Protection Policy](https://prrvchr.github.io/gDriveOOo/gDriveOOo/registration/PrivacyPolicy_en)

## gDriveOOo v.0.0.4


### Google Drive implementation for LibreOffice / OpenOffice.

![gDriveOOo screenshot](gDrive.png)


### Use:

#### Install [OAuth2OOo](https://github.com/prrvchr/OAuth2OOo/releases/download/v0.0.4/OAuth2OOo.oxt) extention v 0.0.4.

You must install this extention first!!!

Restart LibreOffice / OpenOffice after installation.

#### Install [gDriveOOo](https://github.com/prrvchr/gDriveOOo/releases/download/v0.0.4/gDriveOOo.oxt) extention v 0.0.4.

Restart LibreOffice / OpenOffice after installation.


### Requirement:

gDriveOOo uses a local Hsqldb database of version 2.5.x.  
The use of Hsqldb requires the installation and configuration within LibreOffice / OpenOffice  
of a **JRE version 1.8 minimum** (ie: Java version 8)

Sometimes it may be necessary for LibreOffice users must have no Hsqldb driver installed with LibreOffice  
(check your Installed Application under Windows or your Packet Manager under Linux)  
OpenOffice doesn't seem to need this workaround.


### Configure LibreOffice Open / Save dialogs:

#### For LibreOffice V5.x and before:

In menu Tools - Options - LibreOffice - General: check use LibreOffice dialogs.

#### For LibreOffice V6.x and above:

In menu Tools - Options - LibreOffice - Advanced - Open Expert Configuration

Search for: UseSystemFileDialog (Found under: org.openoffice.Office.Common > Misc)

Edit or change "true" to "false" (set it to "false")


### Open your Google Drive:

In File - Open - File name enter: vnd.google-apps://your_account/ or vnd.google-apps:///

If you don't give your_account, you will be asked for...

After authorizing the OAuthOOo application to access your Drive, your Google Drive should open!!! normally  ;-)


### Has been tested with:

* LibreOffice 6.0.4.2 - Ubuntu 17.10 -  LxQt 0.11.1

* OpenOffice 4.1.5 x86_64 - Ubuntu 17.10 - LxQt 0.11.1

I encourage you in case of problem :-(  
to create an [issue](https://github.com/prrvchr/gDriveOOo/issues/new)  
I will try to solve it ;-)
