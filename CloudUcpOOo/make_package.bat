
cd .\CloudUcpOOo

..\zip.exe -0 CloudUcpOOo.zip mimetype

..\zip.exe -r CloudUcpOOo.zip *

cd ..

move /Y .\CloudUcpOOo\CloudUcpOOo.zip .\CloudUcpOOo.oxt
