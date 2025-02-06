#!/bin/bash

# Disable and stop currently running services
bash -x ~/flash-tv-scripts/services/stop_services.sh

# Copy, load, and enable services
sudo cp ~/flash-tv-scripts/services/flash-run-on-boot.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/services/flash-periodic-restart.service /etc/systemd/system

# Reload the systemctl daemon
sudo systemctl daemon-reload
