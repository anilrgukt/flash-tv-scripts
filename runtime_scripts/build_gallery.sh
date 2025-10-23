#!/bin/bash

if [ $# -lt 3 ]; then
    echo "Usage: $0 <participant_id> <username> <data_folder_path>"
    echo "Example: $0 123 flashsys001 /home/flashsys001/data/123001_data"
    exit 1
fi

participant_id="$1"
username="$2"
DATA_FOLDER_PATH="$3"

echo "Starting gallery creation with:"
echo "  Participant ID: ${participant_id}"
echo "  Username: ${username}"
echo "  Data Path: ${DATA_FOLDER_PATH}"

# Activate Python virtual environment
source "/home/${username}/py38/bin/activate"

# Launch gallery creation Python script
python "/home/${username}/flash-tv-scripts/python_scripts/cv2_capture_automate.py" "${participant_id}" "${DATA_FOLDER_PATH}" "${username}"



