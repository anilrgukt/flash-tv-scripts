#!/bin/bash

if [ $# -lt 3 ]; then
    echo "Usage: $0 <participant_id> <username> <data_folder_path> [old_device_id] [new_device_id]"
    echo "Example: $0 123 flashsys001 /home/flashsys001/data/123001_data"
    echo "Optional: $0 123 flashsys001 /home/flashsys001/data/123001_data 001 002"
    exit 1
fi

participant_id="$1"
username="$2"
DATA_FOLDER_PATH="$3"

if [ "$#" -eq 5 ]; then
  old_device_id=$4
  new_device_id=$5
elif [ "$#" -eq 3 ]; then
  read -rp 'Enter the ID of the device you are transferring faces FROM (3 digits): ' old_device_id
  read -rp 'Enter the ID of the device you are transferring faces TO (3 digits): ' new_device_id
else
  echo "Invalid number of arguments. Either provide 3 (participant, username, data_path) or 5 (+ old_device, new_device)"
  exit 1
fi

for folder in "${DATA_FOLDER_PATH}"/*; do
  if [[ "${folder}" == *faces* ]]; then
    FACES_FOLDER_PATH="${folder}"
    break
  fi
done

NEW_FACES_FOLDER_PATH="${FACES_FOLDER_PATH/${old_device_id}/${new_device_id}}"
mv -v "${FACES_FOLDER_PATH}" "${NEW_FACES_FOLDER_PATH}"

cd "${NEW_FACES_FOLDER_PATH}" || exit 1
for image in *; do
  [[ -f "$image" ]] || continue
  new_image="${image/${old_device_id}/${new_device_id}}"
  mv -v "${image}" "${new_image}"
done
