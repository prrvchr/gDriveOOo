#!/bin/bash

cd ./make_odb

./make_odb.sh

cd ..

cd ./gDriveOOo/

zip -0 gDriveOOo.zip mimetype

zip -r gDriveOOo.zip *

cd ..

mv ./gDriveOOo/gDriveOOo.zip ./gDriveOOo.oxt
