#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

# Set to exit on non-zero error code
set -e

# Setting up plug ID for Home Assistant config file
read -p 'Enter plug ID (4 characters lowercase) or YYYY (uppercase) if the plug is not yet ready:' plugID

zenity --question --title="Verify Plug ID" --width 500 --height 100 --text="Please verify the following details\nPlug ID: $plugID" --no-wrap
user_resp=$?

if [ $user_resp -eq 1 ]; then
	#echo "Exitted the code $user_resp"
	zenity --warning --text="Exiting the code since data details are not correct. Please modify them and restart the script."
	exit 1
fi

sed -i "s/YYYY/$plugID/g" ~/flash-tv-scripts/install_scripts/configuration.yaml

bash -x ~/flash-tv-scripts/setup_scripts/id_setup.sh
bash -x ~/flash-tv-scripts/setup_scripts/service_setup.sh


# Copying the config file to the Home Assistant directory
cp ~/flash-tv-scripts/install_scripts/configuration.yaml ~/.homeassistant
