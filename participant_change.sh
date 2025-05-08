#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

# Prompt user for the smart plug ID, FLASH device ID, participant ID, and Bluetooth beacon accelerometer MAC address
smart_plug_id=$(zenity --entry --width 500 --height 100 --text="Enter the Zigbee smart plug ID's extra index at the end, displayed in Home Assistant.\n\nLeave blank if no extra index.\n\nEnter YYYY (uppercase) if the smart plug is not ready:")

flash_device_id=$(zenity --entry --width 500 --height 100 --text="Enter the current FLASH device's ID (3 digits at the end of the username):")

participant_id=$(zenity --entry --width 500 --height 100 --text="Enter the participant ID (P1-1[3 digits no brackets] for TECH):")

if zenity --question --title="Are you using Bluetooth beacon accelerometer(s) for this visit?" --width 500 --height 100 --text="Are you using Bluetooth beacon accelerometer(s) for this visit?" --no-wrap; then
	echo "Scanning for Bluetooth beacon accelerometer MAC addresses... please wait around 30 seconds. You might need to enter the password first."
	unique_mac_addresses="$(sudo bash "/home/flashsys${flash_device_id}/flash-tv-scripts/services/run_bluetooth_beacon_accelerometer_searcher.sh" flashsys"${flash_device_id}")"
	# Function to validate MAC address format (XX:XX:XX:XX:XX:XX)
	validate_mac_address() {
	    local mac=$1
	    # Check if MAC address has exactly 6 pairs of hexadecimal digits separated by colons
	    if [[ $mac =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
		return 0
	    else
		return 1
	    fi
	}
    while true; do
        if ! bluetooth_beacon_mac_address=$(zenity --entry --width 500 --height 100 --text="Enter the Bluetooth beacon accelerometer's MAC address (format: XX:XX:XX:XX:XX:XX).\n\nUnique MAC Addresses found:\n${unique_mac_addresses}"); then
            exit 1
        else
            if validate_mac_address "${bluetooth_beacon_mac_address}"; then
                break
            else
                zenity --warning --text="The MAC address ${bluetooth_beacon_mac_address} was invalid.\n\nPlease enter a valid MAC address in the format XX:XX:XX:XX:XX:XX." --width 500 --height 100
            fi
        fi
    done

else
	bluetooth_beacon_mac_address="Not Needed for this Visit"
fi

if ! zenity --question --title="Verify Details" --width 500 --height 100 --text="Please verify the following details\n\nPlug ID: $smart_plug_id\nFamily ID: ${participant_id}\nDevice ID: ${flash_device_id}\nBluetooth Beacon Accelerometer MAC Address: ${bluetooth_beacon_mac_address}" --no-wrap; then
    zenity --warning --text="Exiting the code since the smart plug ID, FLASH device ID, participant ID, and/or Bluetooth beacon accelerometer MAC address were not entered correctly according to the user. Please restart the script to try again." --width 500 --height 100
    exit 1
fi

# Update the target MAC address in the Bluetooth beacon accelerometer data reader code
sed -i "s/ZZZZ/${bluetooth_beacon_mac_address}/g" ~/flash-tv-scripts/services/bluetooth_beacon_accelerometer_data_reader.c

# Set to exit on non-zero error code
set -e

# Update the configuration.yaml with the plug ID
sed -i "s/YYYY/${smart_plug_id}/g" "${HOME}/flash-tv-scripts/install_scripts/configuration.yaml"


HOME_ASSISTANT_FOLDER="${HOME}/homeassistant-compose"
if [ ! -d "${HOME_ASSISTANT_FOLDER}" ]; then
	bash "${HOME}/flash-tv-scripts/install_scripts/homeassistant_install.sh"
fi

# Run the ID setup script
bash -x "${HOME}/flash-tv-scripts/setup_scripts/ID_setup.sh" 1 "${flash_device_id}" "${participant_id}"
sleep 1

# Run the USB backup setup script
bash -x "${HOME}/flash-tv-scripts/setup_scripts/USB_backup_setup.sh"
sleep 1

# Run the service setup script
bash -x "${HOME}/flash-tv-scripts/setup_scripts/service_setup.sh"
sleep 1

# Run the RTC setup script
bash -x "${HOME}/flash-tv-scripts/setup_scripts/RTC_setup.sh"
sleep 1

# Copy modified configuration.yaml with plug ID to Home Assistant folder after updating the family and device IDs as well
#sudo cp "/home/flashsys${flash_device_id}/flash-tv-scripts/install_scripts/configuration.yaml" "/home/flashsys${flash_device_id}/homeassistant-compose/config/configuration.yaml"

# # Start the Home Assistant Docker compose instance
# cd "${HOME}/homeassistant-compose/config"

# docker compose up -d

# Copy git config into data folder
cp "${HOME}/flash-tv-scripts/.git/config" "${HOME}/data/${participant_id}${flash_device_id}_data/git_config.txt"
