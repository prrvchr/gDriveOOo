#!/bin/bash

cd ./gDriveOOo/
zip -0 gDriveOOo.zip mimetype
zip -r gDriveOOo.zip *
cd ..

mv ./gDriveOOo/gDriveOOo.zip ./gDriveOOo.oxt
