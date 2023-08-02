#!/bin/bash

# Restart all services
sudo systemctl restart flash-periodic-restart.service
sleep 1;
sudo systemctl restart flash-run-on-boot.service
sleep 1;
sudo systemctl restart homeassistant-run-on-boot.service
