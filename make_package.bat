
rem cd .\make_odb
rem call .\make_odb.bat
rem cd ..

cd .\gDriveOOo

..\zip.exe -0 gDriveOOo.zip mimetype

..\zip.exe -r gDriveOOo.zip *

cd ..

move /Y .\gDriveOOo\gDriveOOo.zip .\gDriveOOo.oxt
