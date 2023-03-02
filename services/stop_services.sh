#!/bin/bash

# Disable all services
sudo systemctl disable flash-periodic-restart.service
sudo systemctl disable flash-run-on-boot.service
sudo systemctl disable homeassistant-run-on-boot.service

# Stop all services
sudo systemctl stop flash-periodic-restart.service
sudo systemctl stop flash-run-on-boot.service
sudo systemctl stop homeassistant-run-on-boot.service
