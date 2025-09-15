#!/bin/bash

# Restart all services
sudo systemctl restart flash-periodic-restart.service
sleep 1;
sudo systemctl restart flash-run-on-boot.service
sleep 1;

# Restart Home Assistant Docker container
cd "${HOME}/homeassistant-compose" || exit
docker compose restart

#Display the status of all services
sudo systemctl status --no-pager flash-periodic-restart.service flash-run-on-boot.service
