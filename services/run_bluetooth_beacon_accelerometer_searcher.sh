#!/bin/bash
username=$1

SEARCHER_PROGRAM_PATH="/home/${username}/flash-tv-scripts/services/bluetooth_beacon_accelerometer_searcher"

cc "${SEARCHER_PROGRAM_PATH}.c" -lbluetooth -o "${SEARCHER_PROGRAM_PATH}"

# Restart the Bluetooth service
sudo systemctl restart bluetooth.service

sleep 2;

# Run the program
output="$(sudo "${SEARCHER_PROGRAM_PATH}" | tr ', ' '\n' | sort | uniq)"

# Output each entry on a new line
echo "$output" | tr ' ' '\n'

