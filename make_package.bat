
cd .\make_odb

call .\make_odb.bat

cd ..

cd .\gDriveOOo

..\zip -0 gDriveOOo.zip mimetype

..\zip -r gDriveOOo.zip *

cd ..

move /Y .\gDriveOOo\gDriveOOo.zip .\gDriveOOo.oxt
