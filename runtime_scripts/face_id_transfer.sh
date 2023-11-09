#!/bin/bash

if [ "$#" -eq 2 ]; then

  echo "Command Line Usage: $0 (ID of Device You are Transferring Faces FROM) (ID of Device You are Transferring Faces TO)"
  read -p 'Enter the ID of the device you are transferring faces FROM (3 digits):' olddeviceID
  read -p 'Enter the ID of the device you are transferring faces TO (3 digits):' newdeviceID
  
else

  olddeviceID=$1
  newdeviceID=$2
  
fi

facefolder=`ls ~/data/123XXX_data/ | grep faces`

cd ~/data/123XXX_data/

mv -v "$facefolder" "${facefolder/$olddeviceID/$newdeviceID}"

faceimages=`ls ~/data/123XXX_data/123XXX_faces/`

cd ~/data/123XXX_data/123XXX_faces/

for faceimage in $faceimages
do
  mv -v "$faceimage" "${faceimage/$olddeviceID/$newdeviceID}"
done


