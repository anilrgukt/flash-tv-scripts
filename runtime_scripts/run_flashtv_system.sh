#!/bin/bash

# Check if required arguments are provided
if [ $# -lt 3 ]; then
    echo "Usage: $0 <participant_id> <username> <data_folder_path>"
    echo "Example: $0 123 flashsys001 /home/flashsys001/data/123001_data"
    exit 1
fi

# Get arguments from command line
participant_id="$1"
username="$2"
DATA_FOLDER_PATH="$3"

echo "Starting FLASH-TV system with:"
echo "  Participant ID: ${participant_id}"
echo "  Username: ${username}"
echo "  Data Path: ${DATA_FOLDER_PATH}"

# Check whether or not the available camera(s) is/are being used by other programs
video_device_list=$(ls /dev/video*)
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

if [ ${user_resp} -eq 1 ]; then
	zenity --warning --text="Exiting the code since the data details were not correct according to the user. Please modify them and restart the script."
	exit 
fi

# Source .bashrc to obtain path variables set up beforehand
source "/home/${username}/.bashrc"
echo "PYTHON_PATH is" "${PYTHON_PATH}"

# Confirm the start of the algorithm
zenity --question --title="About to run FLASH-TV algorithm" --width 500 --height 100 --text="Click Yes to start video streaming" --no-wrap
user_resp=$?

if [ ${user_resp} -eq 1 ]; then
	echo "Exiting the code due to the user clicking No"
	exit 
fi

# Activate Python 3.8 virtual environment with libraries set up
source "/home/${username}/py38/bin/activate"

# Run a while loop for the FLASH-TV algorithm only if it doesn't already exist
while true;
do
if ! [ "$(pgrep -af run_flash_data_collection.py)" ]; then
	free -m && sync && echo 1 > /proc/sys/vm/drop_caches && free -m;

 	sleep 1;

	python "/home/${username}/flash-tv-scripts/python_scripts/run_flash_data_collection.py" "${participant_id}" "${DATA_FOLDER_PATH}" save-image "${username}";

	sleep 30;
else
	sleep 30;
fi
done
	



