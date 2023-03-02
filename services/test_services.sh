#!/bin/bash

# Enable all services
sudo systemctl enable flash-periodic-restart.service
sudo systemctl enable flash-run-on-boot.service
sudo systemctl enable homeassistant-run-on-boot.service

# Start all services
sudo systemctl start flash-periodic-restart.service
sudo systemctl start flash-run-on-boot.service
sudo systemctl start homeassistant-run-on-boot.service

#Display the status of all services
echo `sudo systemctl status flash-periodic-restart.service`
echo `sudo systemctl status flash-run-on-boot.service`
echo `sudo systemctl status homeassistant-run-on-boot.service`
