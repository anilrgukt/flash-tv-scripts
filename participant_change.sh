#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

HOME_ASSISTANT_FOLDER="${HOME}/docker-compose/ha-config"
if [ ! -d "${HOME_ASSISTANT_FOLDER}" ]; then
    zenity --warning --text="Exiting the code since Home Assistant has not been set up.\n\nPlease set up Home Assistant before running this script." --width 500 --height 100
    exit 1
fi

# Prompt user for the smart plug ID, FLASH device ID, participant ID, and Bluetooth beacon accelerometer MAC address
smart_plug_id=$(zenity --entry --width 500 --height 100 --text="Enter the Zigbee smart plug ID's extra index at the end, displayed in Home Assistant. Leave blank if no extra index. Enter YYYY (uppercase) if the smart plug is not ready:")

flash_device_id=$(zenity --entry --width 500 --height 100 --text="Enter the current FLASH device's ID (3 digits at the end of the username):")

participant_id=$(zenity --entry --width 500 --height 100 --text="Enter the participant ID (P1-1[3 digits no brackets] for TECH):")

# Run the Bluetooth beacon scanner script
bash ~/flash-tv-scripts/services/run_bluetooth_beacon_scanner.sh &

# Wait for a few seconds to gather some MAC addresses
sleep 10

# Display unique MAC addresses
unique_mac_addresses=$(sort -u /home/unique_mac_addresses.txt)
zenity --info --width 500 --height 300 --text="Unique MAC addresses detected:\n\n${unique_mac_addresses}"

bluetooth_beacon_mac_address=$(zenity --entry --width 500 --height 100 --text="Enter the Bluetooth beacon accelerometer's MAC address (format: XX:XX:XX:XX:XX:XX):")

zenity --question --title="Verify the smart plug ID, FLASH device ID, participant ID, and Bluetooth beacon accelerometer MAC address" --width 500 --height 100 --text="Please verify the following details\n\nPlug ID: $smart_plug_id\nFamily ID: ${participant_id}\nDevice ID: ${flash_device_id}\nMAC Address: ${bluetooth_beacon_mac_address}" --no-wrap
user_resp=$?

if [ ${user_resp} -eq 1 ]; then
    zenity --warning --text="Exiting the code since the smart plug ID, FLASH device ID, participant ID, and/or Bluetooth beacon accelerometer MAC address were not entered correctly according to the user. Please restart the script to try again." --width 500 --height 100
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
if ! validate_mac_address "${bluetooth_beacon_mac_address}"; then
    zenity --warning --text="The MAC address's format was invalid. Please enter a valid MAC address in the format XX:XX:XX:XX:XX:XX." --width 500 --height 100
    exit 1
fi

# Update the target MAC address in the Bluetooth beacon accelerometer scanner code
sed -i "s/ZZZZ/${bluetooth_beacon_mac_address}/g" ~/flash-tv-scripts/services/bluetooth_beacon_accelerometer_scanner.c

# Set to exit on non-zero error code
set -e

# Update the configuration.yaml with the plug ID
sed -i "s/YYYY/${smart_plug_id}/g" "${HOME}/flash-tv-scripts/install_scripts/configuration.yaml"

# Run the ID setup script
bash -x "${HOME}/flash-tv-scripts/setup_scripts/ID_setup.sh" "${flash_device_id}" "${participant_id}" 1
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
sudo cp "/home/flashsys${flash_device_id}/flash-tv-scripts/install_scripts/configuration.yaml" "/home/flashsys${flash_device_id}/docker-compose/ha-config/configuration.yaml"

# Start the Home Assistant Docker compose instance
cd "${HOME}/docker-compose/ha-config"

docker compose up -d

# Copy git config into data folder
cp "${HOME}/flash-tv-scripts/.git/config" "${HOME}/data/${participant_id}${flash_device_id}_data/git_config.txt"
