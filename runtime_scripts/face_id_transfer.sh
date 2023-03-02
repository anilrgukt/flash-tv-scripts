#!/bin/bash

read -p 'Enter the ID of the device you are transferring faces FROM (3 digits):' olddeviceID
read -p 'Enter the ID of the device you are transferring faces TO (3 digits):' newdeviceID

facefolder=`ls ~/data/123XXX_data/ | grep faces`

cd ~/data/123XXX_data/

mv -v "$facefolder" "${facefolder/$olddeviceID/$newdeviceID}"

faceimages=`ls ~/data/123XXX_data/123XXX_faces/`

cd ~/data/123XXX_data/123XXX_faces/

for faceimage in $faceimages
do
  mv -v "$faceimage" "${faceimage/$olddeviceID/$newdeviceID}"
done


