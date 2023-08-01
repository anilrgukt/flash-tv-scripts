#!/bin/bash

# Restart all services
sudo systemctl restart flash-periodic-restart.service
sudo systemctl restart flash-run-on-boot.service
sudo systemctl restart homeassistant-run-on-boot.service
sudo systemctl restart daily-reboot.service
