#!/bin/bash

# Stop all services
sudo systemctl stop flash-periodic-restart.service
sleep 1;
sudo systemctl stop flash-run-on-boot.service
sleep 1;
sudo systemctl stop homeassistant-run-on-boot.service
sleep 1;

# Disable all services
sudo systemctl disable flash-periodic-restart.service
sleep 1;
sudo systemctl disable flash-run-on-boot.service
sleep 1;
sudo systemctl disable homeassistant-run-on-boot.service


