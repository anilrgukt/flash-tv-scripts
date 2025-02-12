#!/bin/bash

BLUETOOTH_BEACON_SCANNER_PROGRAM_PATH="/home/${username}/flash-tv-scripts/services/bluetooth_beacon_accelerometer_data_reader"

if [ ! -e "${BLUETOOTH_BEACON_SCANNER_PROGRAM_PATH}" ]; then
    cc "${BLUETOOTH_BEACON_SCANNER_PROGRAM_PATH}.c" -lbluetooth -o "${BLUETOOTH_BEACON_SCANNER_PROGRAM_PATH}"
fi

while true; do
  # Run the program
  sudo "${BLUETOOTH_BEACON_SCANNER_PROGRAM_PATH}"
  
  # Wait for the program to exit
  wait $!
  
  # Restart the Bluetooth service
  sudo systemctl restart bluetooth.service
  
  # Sleep for 5 seconds
  sleep 5
  
  # Restart the program
done
