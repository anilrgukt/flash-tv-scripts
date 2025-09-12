#!/bin/bash

# Enable all services
sudo systemctl enable flash-periodic-restart.service
sleep 1;
sudo systemctl enable flash-run-on-boot.service
sleep 1;

# Start all services
sudo systemctl start flash-periodic-restart.service
sleep 1;
sudo systemctl start flash-run-on-boot.service
sleep 1;

# Start Home Assistant Docker container
cd "${HOME}/homeassistant-compose" || exit
docker compose up -d

# Display the status of all services
sudo systemctl status --no-pager flash-periodic-restart.service flash-run-on-boot.service
docker ps -a