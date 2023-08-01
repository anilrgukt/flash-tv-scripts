#!/bin/bash

# Enable all services
sudo systemctl enable flash-periodic-restart.service
sudo systemctl enable flash-run-on-boot.service
sudo systemctl enable homeassistant-run-on-boot.service
sudo systemctl enable daily-reboot.service

# Start all services
sudo systemctl start flash-periodic-restart.service
sudo systemctl start flash-run-on-boot.service
sudo systemctl start homeassistant-run-on-boot.service
sudo systemctl start daily-reboot.service

#Display the status of all services
systemctl status flash-periodic-restart.service flash-run-on-boot.service homeassistant-run-on-boot.service daily-reboot.service
