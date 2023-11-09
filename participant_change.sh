#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

if [ ! -d ~/.homeassistant ]; then
	zenity --warning --text="Exiting the code since Home Assistant has not been set up.\n\nPlease set up Home Assistant before running this script." --width 500 --height 100
	exit 1
fi

skip_checking=0

if [ "$#" -ne 3 ]; then

	if [ "$#" -eq 4 ]; then

		plugID=$1
		deviceID=$2
		familyID=$3
  		skip_checking=$4

 	else

		echo "Command Line Usage: $0 (plugID) (deviceID) (familyID)"
		
		# Setting up plug ID for Home Assistant config file
		plugID=$(zenity --entry --width 500 --height 100 --text="Enter plug ID (4 characters lowercase) or YYYY (uppercase) if the plug is not ready:")
		
		deviceID=$(zenity --entry --width 500 --height 100 --text="Enter FLASH device ID (3 digits):")
		
		familyID=$(zenity --entry --width 500 --height 100 --text="Enter family ID (3 digits for Study 4, P1-1[3 digits no brackets] for TECH):")
 	fi
   
else

 	plugID=$1
	deviceID=$2
	familyID=$3
  
fi

if [ $skip_checking -ne 1]; then

	zenity --question --title="Verify Plug ID, Device ID, and Family ID" --width 500 --height 100 --text="Please verify the following details\n\nPlug ID: $plugID\nFamily ID: ${familyID}\nDevice ID: ${deviceID}" --no-wrap
	user_resp=$?
	
	if [ ${user_resp} -eq 1 ]; then
		zenity --warning --text="Exiting the code since the plug ID, device ID, and/or family ID were not entered correctly according to the user. Please restart the script to try again." --width 500 --height 100
		exit 1
	fi
fi

# Set to exit on non-zero error code
set -e

sed -i "s/YYYY/$plugID/g" ~/flash-tv-scripts/install_scripts/configuration.yaml

bash -x ~/flash-tv-scripts/setup_scripts/ID_setup.sh $deviceID $familyID 1
sleep 1;

bash -x ~/flash-tv-scripts/setup_scripts/USB_backup_setup.sh
sleep 1;

bash -x ~/flash-tv-scripts/setup_scripts/service_setup.sh
sleep 1;

bash -x ~/flash-tv-scripts/setup_scripts/RTC_setup.sh
sleep 1;

cp ~/flash-tv-scripts/install_scripts/configuration.yaml ~/.homeassistant


