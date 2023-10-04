#!/bin/bash

# Set up RTC
sudo sed -i 's/ATTR{hctosys}=="1"/ATTR{hctosys}=="0"/g' /lib/udev/rules.d/50-udev-default.rules

timedatectl set-ntp 1
sleep 5;
sudo systemctl restart systemd-timesyncd.service
sleep 5;
sudo hwclock -w

source ~/py38/bin/activate
python3 ~/flash-tv-scripts/python_scripts/update_ext_ds3231_from_dt_now.py

# Disable and stop currently running services
bash -x ~/flash-tv-scripts/services/stop_services.sh

# Copy, load, and enable services
sudo cp ~/flash-tv-scripts/services/flash-run-on-boot.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/services/flash-periodic-restart.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/services/homeassistant-run-on-boot.service /etc/systemd/system

sudo systemctl daemon-reload
