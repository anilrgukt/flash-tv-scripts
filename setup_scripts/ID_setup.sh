#!/bin/bash

# Remove video capture and internal testing folder just in case as they are intended for use with a laptop and unnecessary for the devices that are being installed in the home
rm -r "${HOME}/flash-tv-scripts/video_capture_scripts"
rm -r "${HOME}/flash-tv-scripts/internal_testing"

skip_checking=$1
flash_device_id=$2
participant_id=$3


if [ "${skip_checking}" -ne 1 ]; then
	flash_device_id=$(zenity --entry --width 500 --height 100 --text="Enter the current FLASH device's ID (3 digits at the end of the username):")
	
	participant_id=$(zenity --entry --width 500 --height 100 --text="Enter the participant ID (P1-1[3 digits no brackets] for TECH):")

	zenity --question --title="Verify the FLASH device ID and participant ID" --width 500 --height 100 --text="Please verify the following details\nParticipant ID: ${participant_id}\nFLASH Device ID: ${flash_device_id}" --no-wrap
	user_resp=$?

	if [ "${user_resp}" -eq 1 ]; then
		zenity --warning --text="Exiting the code since the FLASH device ID and participant ID were not entered correctly according to the user. Please restart the script to try again." --width 500 --height 100
		exit 1
	fi
fi

# Create data directory
mkdir "${HOME}/data"
mkdir "${HOME}/data/${participant_id}${flash_device_id}_data"

# Replace device (XXX) and participant ID (123) placeholders with actual input
sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/services/flash-periodic-restart.service"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/services/flash-periodic-restart.service"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/services/flash_periodic_restart.sh"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/services/flash_periodic_restart.sh"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/services/flash-run-on-boot.service"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/services/flash-run-on-boot.service"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/services/flash_run_on_boot.sh"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/services/flash_run_on_boot.sh"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/install_scripts/compose.yaml"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/install_scripts/compose.yaml"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/homeassistant-compose/compose.yaml"
sed -i "s/123/${participant_id}/g" "${HOME}/homeassistant-compose/compose.yaml"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/runtime_scripts/build_gallery.sh"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/runtime_scripts/build_gallery.sh"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/runtime_scripts/create_faces.sh"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/runtime_scripts/create_faces.sh"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/runtime_scripts/run_flashtv_system.sh"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/runtime_scripts/run_flashtv_system.sh"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/runtime_scripts/face_ID_transfer.sh"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/runtime_scripts/face_ID_transfer.sh"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/install_scripts/configuration.yaml"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/install_scripts/configuration.yaml"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/setup_scripts/USB_backup_setup.sh"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/setup_scripts/USB_backup_setup.sh"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/setup_scripts/RTC_setup.sh"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/setup_scripts/RTC_setup.sh"

sed -i "s/XXX/${flash_device_id}/g" "${HOME}/flash-tv-scripts/services/bluetooth_beacon_accelerometer_data_reader.c"
sed -i "s/123/${participant_id}/g" "${HOME}/flash-tv-scripts/services/bluetooth_beacon_accelerometer_data_reader.c"
