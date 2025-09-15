#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

# Auto-detect device ID from username (last 3 digits)
flash_device_id=$(basename "$HOME" | grep -o '[0-9]*$')

# Prompt for participant ID
participant_id=$(zenity --entry --width 500 --height 100 --text="Enter the participant ID (P1-[4 digits no brackets] for TECH, ES-[4 digits no brackets] for ESS):")

# Set Bluetooth beacon accelerometer MAC address to default (not used)
bluetooth_beacon_mac_address="Not Needed for this Visit"

if ! zenity --question --title="Verify Details" --width 500 --height 100 --text="Please verify the following details\n\nFamily ID: ${participant_id}\nDevice ID: ${flash_device_id} (auto-detected)" --no-wrap; then
    zenity --warning --text="Exiting the code since the participant ID and/or device ID were not correct according to the user. Please restart the script to try again." --width 500 --height 100
    exit 1
fi

# Update the target MAC address in the Bluetooth beacon accelerometer data reader code
sed -i "s/ZZZZ/${bluetooth_beacon_mac_address}/g" ~/flash-tv-scripts/services/bluetooth_beacon_accelerometer_data_reader.c

# Set to exit on non-zero error code
set -e

# Skip smart plug configuration (not used)


HOME_ASSISTANT_FOLDER="${HOME}/homeassistant-compose"
if [ ! -d "${HOME_ASSISTANT_FOLDER}" ]; then
	bash "${HOME}/flash-tv-scripts/install_scripts/homeassistant_install.sh"
fi

# Run the ID setup script
bash -x "${HOME}/flash-tv-scripts/setup_scripts/ID_setup.sh" 1 "${flash_device_id}" "${participant_id}"
sleep 1

# Skip USB backup setup to avoid password prompts

# Run the service setup script
bash -x "${HOME}/flash-tv-scripts/setup_scripts/service_setup.sh"
sleep 1

# Run the RTC setup script
bash -x "${HOME}/flash-tv-scripts/setup_scripts/RTC_setup.sh"
sleep 1

# Copy git config into data folder
cp "${HOME}/flash-tv-scripts/.git/config" "${HOME}/data/${participant_id}${flash_device_id}_data/git_config.txt"

# Copy modified configuration.yaml with plug ID to Home Assistant folder after updating the family and device IDs as well
CONFIG_SOURCE="${HOME}/flash-tv-scripts/install_scripts/configuration.yaml"
CONFIG_DEST="${HOME}/homeassistant-compose/config/configuration.yaml"

# Update configuration.yaml with participant and device IDs
sed -i "s/123XXX/${participant_id}${flash_device_id}/g" "$CONFIG_SOURCE"

# Force copy with sudo to overwrite root-owned files
if [ -f "${CONFIG_DEST}" ]; then
	sudo cp "$CONFIG_SOURCE" "$CONFIG_DEST"
	sudo chown $(whoami):$(whoami) "$CONFIG_DEST"
 	cd "${HOME}/homeassistant-compose/config"
  	docker compose up -d
   	sleep 5
    	firefox --new-window http://localhost:8123/history >/dev/null 2>&1 &
     	sleep 1
     	zenity --info --text="Please look at the History tab of the window that was just opened, and verify that power data is being received once the TV is plugged into the smart plug." --width 500 --height 100
      	exit 0
else
	zenity --warning --text=echo "Home Assistant configuration.yaml file not created yet, skipping configuration.yaml update. Set up Home Assistant and either run this again or manually copy the configuration.yaml later."  --width 500 --height 100
 	exit 0
fi
