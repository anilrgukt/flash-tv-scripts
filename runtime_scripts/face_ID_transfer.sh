#!/bin/bash

# Data details
participant_id=123XXX
username=flashsysXXX
DATA_FOLDER_PATH="/home/${username}/data/${participant_id}_data"

# If there aren't exactly 2 command line arguments, prompt the user for the old device ID and the new device ID
if [ "$#" -ne 2 ]; then
  echo "Command Line Usage: $0 (ID of Device You are Transferring Faces FROM) (ID of Device You are Transferring Faces TO)"
  read -rp 'Enter the ID of the device you are transferring faces FROM (3 digits): ' old_device_id
  read -rp 'Enter the ID of the device you are transferring faces TO (3 digits): ' new_device_id
else
  old_device_id=$1
  new_device_id=$2
fi

# Find the faces folder within the data folder
for folder in "${DATA_FOLDER_PATH}"/*; do
  if [[ "${folder}" == *faces* ]]; then
    FACES_FOLDER_PATH="${folder}"
    break
  fi
done

# Replace the old device ID with the new device ID within the faces folder path (syntax is specific)
NEW_FACES_FOLDER_PATH="${FACES_FOLDER_PATH/${old_device_id}/${new_device_id}}"
mv -v "${FACES_FOLDER_PATH}" "${NEW_FACES_FOLDER_PATH}"

# Replace the old device ID with the new device ID within each face image path (syntax is specific)
cd "${NEW_FACES_FOLDER_PATH}" || exit 1
for image in *; do
  [[ -f "$image" ]] || continue
  new_image="${image/${old_device_id}/${new_device_id}}"
  mv -v "${image}" "${new_image}"
done
