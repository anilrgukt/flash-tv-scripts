#!/bin/bash

# Enable all services
sudo systemctl enable flash-periodic-restart.service
sleep 1;
sudo systemctl enable flash-run-on-boot.service
sleep 1;
sudo systemctl enable homeassistant-run-on-boot.service
sleep 1;

# Start all services
sudo systemctl start flash-periodic-restart.service
sleep 1;
sudo systemctl start flash-run-on-boot.service
sleep 1;
sudo systemctl start homeassistant-run-on-boot.service
sleep 1;

#Display the status of all services
systemctl status flash-periodic-restart.service flash-run-on-boot.service homeassistant-run-on-boot.service
