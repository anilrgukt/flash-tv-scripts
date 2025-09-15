#!/bin/bash
username=$1
DATA_READER_PROGRAM_PATH="/home/${username}/flash-tv-scripts/services/bluetooth_beacon_accelerometer_data_reader"

cc "${DATA_READER_PROGRAM_PATH}.c" -lbluetooth -o "${DATA_READER_PROGRAM_PATH}"


while true; do
  # Run the program
  sudo "${DATA_READER_PROGRAM_PATH}"
  
  # Wait for the program to exit
  wait $!
  
  # Restart the Bluetooth service
  sudo systemctl restart bluetooth.service
  
  # Sleep for 5 seconds
  sleep 5
  
  # Restart the program
done
