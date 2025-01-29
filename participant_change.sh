#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

if [ ! -d "${HOME}/docker-compose/ha-config" ]; then
	zenity --warning --text="Exiting the code since Home Assistant has not been set up.\n\nPlease set up Home Assistant before running this script." --width 500 --height 100
	exit 1
fi


# Prompt user for plugID, deviceID, participantID, and MAC address

plugID=$(zenity --entry --width 500 --height 100 --text="Enter the Zigbee plug ID extra index from Home Assistant, leave blank if no extra index, or YYYY (uppercase) if the plug is not ready:")

deviceID=$(zenity --entry --width 500 --height 100 --text="Enter the FLASH device ID (3 digits):")

participantID=$(zenity --entry --width 500 --height 100 --text="Enter the participant ID (P1-1XXX for TECH):")

mac_address=$(zenity --entry --width 500 --height 100 --text="Enter the MAC address (format: XX:XX:XX:XX:XX:XX):")

zenity --question --title="Verify Plug ID, Device ID, Family ID, and MAC Address" --width 500 --height 100 --text="Please verify the following details\n\nPlug ID: $plugID\nFamily ID: ${participantID}\nDevice ID: ${deviceID}\nMAC Address: ${mac_address}" --no-wrap
user_resp=$?

if [ ${user_resp} -eq 1 ]; then
	zenity --warning --text="Exiting the code since the plug ID, device ID, family ID, or MAC address were not entered correctly according to the user. Please restart the script to try again." --width 500 --height 100
	exit 1
fi

# Function to validate MAC address format (XX:XX:XX:XX:XX:XX)
validate_mac_address() {
    local mac=$1
    # Check if MAC address has exactly 6 pairs of hexadecimal digits separated by colons
    if [[ $mac =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
        return 0  # Valid MAC address
    else
        return 1  # Invalid MAC address
    fi
}

# Validate the MAC address format
if ! validate_mac_address "${mac_address}"; then
    zenity --warning --text="The MAC address format is invalid. Please enter a valid MAC address in the format XX:XX:XX:XX:XX:XX." --width 500 --height 100
    exit 1
fi

# Update the target MAC address in the C code
sed -i "s/ZZZZ/${mac_address}/g" ~/flash-tv-scripts/services/bt_beacon_accelerometer_scanner.c

# Set to exit on non-zero error code
set -e

# Update the configuration.yaml with the plug ID
sed -i "s/YYYY/${plugID}/g" "${HOME}/flash-tv-scripts/install_scripts/configuration.yaml"

bash -x "${HOME}/flash-tv-scripts/setup_scripts/ID_setup.sh" "${deviceID}" "${participantID}" 1
sleep 1

bash -x "${HOME}/flash-tv-scripts/setup_scripts/USB_backup_setup.sh" 1
sleep 1

bash -x "${HOME}/flash-tv-scripts/setup_scripts/service_setup.sh"
sleep 1

bash -x "${HOME}/flash-tv-scripts/setup_scripts/RTC_setup.sh"
sleep 1

# Copy modified configuration.yaml with plug ID to Home Assistant folder after updating the family and device IDs as well
sudo cp "/home/flashsys${deviceID}/flash-tv-scripts/install_scripts/configuration.yaml" "/home/flashsys${deviceID}/docker-compose/ha-config/configuration.yaml"

cd "${HOME}/docker-compose/ha-config"

docker compose up -d

# Copy git config into data folder
cp "${HOME}/flash-tv-scripts/.git/config" "${HOME}/data/${participantID}${deviceID}_data/git_config.txt"

