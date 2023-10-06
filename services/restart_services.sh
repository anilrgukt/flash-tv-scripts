#!/bin/bash

# Restart all services
sudo systemctl restart flash-periodic-restart.service
sleep 1;
sudo systemctl restart flash-run-on-boot.service
sleep 1;
sudo systemctl restart homeassistant-run-on-boot.service
sleep 1;

#Display the status of all services
sudo systemctl status --no-pager flash-periodic-restart.service flash-run-on-boot.service homeassistant-run-on-boot.service
