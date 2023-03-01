#!/bin/bash

# Disable currently running services
sudo systemctl disable flash-periodic-restart.service
sudo systemctl disable flash-run-on-boot.service
sudo systemctl disable homeassistant-run-on-boot.service

# Copy, load, and enable services
sudo cp ~/flash-tv-scripts/flash-run-on-boot.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/flash-periodic-restart.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/homeassistant-run-on-boot.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable flash-periodic-restart.service
sudo systemctl enable flash-run-on-boot.service
sudo systemctl enable homeassistant-run-on-boot.service
