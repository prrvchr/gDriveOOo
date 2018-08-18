
cd .\vnd.google-apps

..\..\zip -0 vnd.google-apps.zip mimetype

..\..\zip -r vnd.google-apps.zip *

cd ..

move /Y .\vnd.google-apps\vnd.google-apps.zip ..\gDriveOOo\vnd.google-apps.odb
