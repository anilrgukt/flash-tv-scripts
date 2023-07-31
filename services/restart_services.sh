#!/bin/bash

# Restart all services
sudo systemctl enable flash-periodic-restart.service
sudo systemctl enable flash-run-on-boot.service
sudo systemctl enable homeassistant-run-on-boot.service
