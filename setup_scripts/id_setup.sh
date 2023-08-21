#!/bin/bash

# Remove video capture and internal testing folder just in case as they are unnecessary for Jetsons
rm -r ~/flash-tv-scripts/video_capture_scripts
rm -r ~/flash-tv-scripts/internal_testing

# Take input
read -p 'Enter FLASH device ID (3 digits):' deviceID
read -p 'Enter family ID (3 digits probably):' familyID

zenity --question --title="Verify Device and Family ID" --width 500 --height 100 --text="Please verify the following details:\n\nFamily ID: $familyID\n\nDevice ID: $deviceID"

user_resp=$?

if [ $user_resp -eq 1 ]; then
	zenity --warning --text="Exiting the code since the data details are not correct.\n\nPlease modify them and restart the script." -width 500 --height 100
	exit 1
fi

# Create data directory
mkdir ~/data
mkdir ~/data/${familyID}${deviceID}_data

# Replace device and family ID placeholders with input
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/services/flash-periodic-restart.service
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/services/flash-periodic-restart.service
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/services/flash_periodic_restart.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/services/flash_periodic_restart.sh
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/services/flash-run-on-boot.service
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/services/flash-run-on-boot.service
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/services/flash_run_on_boot.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/services/flash_run_on_boot.sh
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/services/homeassistant-run-on-boot.service
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/services/homeassistant-run-on-boot.service
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/runtime_scripts/data_details.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/runtime_scripts/data_details.sh
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/runtime_scripts/face_id_transfer.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/runtime_scripts/face_id_transfer.sh
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/install_scripts/configuration.yaml
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/install_scripts/configuration.yaml
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/setup_scripts/USB_backup_setup.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/setup_scripts/USB_backup_setup.sh

