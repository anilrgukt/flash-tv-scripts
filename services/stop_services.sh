#!/bin/bash

# Stop all services
sudo systemctl stop flash-periodic-restart.service
sleep 1;
sudo systemctl stop flash-run-on-boot.service
sleep 1;

# Disable all services
sudo systemctl disable flash-periodic-restart.service
sleep 1;
sudo systemctl disable flash-run-on-boot.service

# Shut down Home Assistant Docker container
cd "${HOME}/docker-compose" || exit
docker compose down
