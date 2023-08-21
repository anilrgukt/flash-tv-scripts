#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

# Setting up plug ID for Home Assistant config file
read -p 'Enter plug ID (4 characters lowercase) or YYYY (uppercase) if the plug is not ready:' plugID

zenity --question --title="Verify Plug ID" --text="Please verify the following details:\n\nPlug ID: $plugID" --width 500 --height 100 

user_resp=$?

if [ $user_resp -eq 1 ]; then

	zenity --warning --text="Exiting the code since the data details are not correct.\n\nPlease modify them and restart the script." --width 500 --height 100
	exit 1

fi

# Set to exit on non-zero error code
set -e

sed -i "s/YYYY/$plugID/g" ~/flash-tv-scripts/install_scripts/configuration.yaml

bash -x ~/flash-tv-scripts/setup_scripts/id_setup.sh
sleep 1;
bash -x ~/flash-tv-scripts/setup_scripts/service_setup.sh
sleep 1;
bash -x ~/flash-tv-scripts/setup_scripts/USB_backup_setup.sh
sleep 1;

# Copying the config file to the Home Assistant directory
cp ~/flash-tv-scripts/install_scripts/configuration.yaml ~/.homeassistant
