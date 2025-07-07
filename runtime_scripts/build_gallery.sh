#!/bin/bash

# Data details
participant_id=123XXX
username=flashsysXXX
DATA_FOLDER_PATH="/home/${username}/data/${participant_id}_data"

# Check whether or not the available camera(s) is/are being used by other programs
video_device_list=$(ls /dev/video* 2>/dev/null || true)
for device in ${video_device_list}
do
	camera_being_used=$(fuser "${device}")
	if [ "${camera_being_used}" ]; then
		zenity --warning --title "Warning Message" --width 500 --height 100 --text "The camera is being used by another program.\nPlease close the other program before continuing."
		exit
	fi
done

# Verify the data details
zenity --question --title="Verifying Data Details" --width 500 --height 100 --text="Please verify the following data details\nParticipant ID: ${participant_id}\nUsername: ${username}\nData Folder Path: ${DATA_FOLDER_PATH}" --no-wrap
user_resp=$?

if [ "${user_resp}" -eq 1 ]; then
	zenity --warning --text="Exiting the code since the data details were not correct according to the user. Please modify them and restart the script."
	exit 
fi

# Confirm the start of the gallery building
zenity --question --title="Building Gallery for FLASH-TV face verification" --width 500 --height 100 --text="Click Yes to start video streaming\nFamily ID: ${participant_id} \nData save path: ${DATA_FOLDER_PATH}" --no-wrap
user_resp=$?

if [ "${user_resp}" -eq 1 ]; then
	echo "Exiting the code due to the user clicking No"
	exit 
fi

# Activate Python 3.8 virtual environment with libraries set up
source "/home/${username}/py38/bin/activate"

# Start the gallery building script
python "/home/${username}/flash-tv-scripts/python_scripts/cv2_capture_automate.py" "${participant_id}" "${DATA_FOLDER_PATH}" "${username}"



