#!/bin/bash

PROGRAM_PATH=$1

while true; do
  # Run the program
  sudo "${PROGRAM_PATH}"
  
  # Wait for the program to exit
  wait $!
  
  # Restart the Bluetooth service
  sudo systemctl restart bluetooth.service
  
  # Sleep for 5 seconds
  sleep 5
  
  # Restart the program
done
