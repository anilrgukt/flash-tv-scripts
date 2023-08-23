#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

if [ ! -d ~/.homeassistant ]; then
	zenity --warning --text="Exiting the code since Home Assistant has not been set up.\n\nPlease set up Home Assistant before running this script." --width 500 --height 100
	exit 1
fi

# Setting up plug ID for Home Assistant config file
plugID=$(zenity --entry --width 500 --height 100 --text="Enter plug ID (4 characters lowercase) or YYYY (uppercase) if the plug is not ready:")

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

bash -x ~/flash-tv-scripts/setup_scripts/USB_backup_setup.sh
sleep 1;

bash -x ~/flash-tv-scripts/setup_scripts/service_setup.sh
sleep 1;

cp ~/flash-tv-scripts/install_scripts/configuration.yaml ~/.homeassistant


