#!/bin/bash

# Remove video capture and internal testing folder just in case as they are unnecessary for Jetsons
rm -r ~/flash-tv-scripts/video_capture_scripts
rm -r ~/flash-tv-scripts/internal_testing

skip_checking=0

if [ "$#" -ne 2 ]; then

	if [ "$#" -eq 3 ]; then

		deviceID=$1
		familyID=$2
  		skip_checking=$3

 	else
	   
    		echo "Command Line Usage: $0 (deviceID) (familyID)"
	   
	   	deviceID=$(zenity --entry --width 500 --height 100 --text="Enter FLASH device ID (3 digits):")
	   
	   	familyID=$(zenity --entry --width 500 --height 100 --text="Enter family ID (3 digits for Study 4, P1-1[3 digits no brackets] for TECH):")

	fi

else
 
  deviceID=$1
  familyID=$2
  
fi

if [ $skip_checking -ne 1]; then
	
 	zenity --question --title="Verify Device and Family ID" --width 500 --height 100 --text="Please verify the following details\nFamily ID: ${familyID}\nDevice ID: ${deviceID}" --no-wrap
	user_resp=$?
	
	if [ ${user_resp} -eq 1 ]; then
		zenity --warning --text="Exiting the code since the device and family ID were not entered correctly according to the user. Please restart the script to try again." --width 500 --height 100
		exit 1
	fi
fi

# Create data directory
mkdir ~/data
mkdir ~/data/${familyID}${deviceID}_data

# Replace device and family ID placeholders with input
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/services/flash-periodic-restart.service
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/services/flash-periodic-restart.service
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/services/flash_periodic_restart.sh
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/services/flash_periodic_restart.sh
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/services/flash-run-on-boot.service
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/services/flash-run-on-boot.service
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/services/flash_run_on_boot.sh
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/services/flash_run_on_boot.sh
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/services/homeassistant-run-on-boot.service
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/services/homeassistant-run-on-boot.service
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/runtime_scripts/data_details.sh
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/runtime_scripts/data_details.sh
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/runtime_scripts/face_ID_transfer.sh
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/runtime_scripts/face_ID_transfer.sh
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/install_scripts/configuration.yaml
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/install_scripts/configuration.yaml
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/setup_scripts/USB_backup_setup.sh
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/setup_scripts/USB_backup_setup.sh
sed -i "s/XXX/${deviceID}/g" ~/flash-tv-scripts/setup_scripts/RTC_setup.sh
sed -i "s/123/${familyID}/g" ~/flash-tv-scripts/setup_scripts/RTC_setup.sh

