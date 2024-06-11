#!/bin/bash

if [ "$#" -ne 2 ]; then

  echo "Command Line Usage: $0 (ID of Device You are Transferring Faces FROM) (ID of Device You are Transferring Faces TO)"
  read -p 'Enter the ID of the device you are transferring faces FROM (3 digits):' olddeviceID
  read -p 'Enter the ID of the device you are transferring faces TO (3 digits):' newdeviceID
  
else

  olddeviceID=$1
  newdeviceID=$2
  
fi

facefolder=`ls ~/data/P1-3344008_data/ | grep faces`

cd ~/data/P1-3344008_data/

mv -v "$facefolder" "${facefolder/$olddeviceID/$newdeviceID}"

faceimages=`ls ~/data/P1-3344008_data/P1-3344008_faces/`

cd ~/data/P1-3344008_data/P1-3344008_faces/

for faceimage in $faceimages
do
  mv -v "$faceimage" "${faceimage/$olddeviceID/$newdeviceID}"
done


