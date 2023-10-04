#!/bin/bash

# Set up RTC
sudo sed -i 's/ATTR{hctosys}=="1"/ATTR{hctosys}=="0"/g' /lib/udev/rules.d/50-udev-default.rules

source ~/py38/bin/activate

timedatectl set-ntp 1
sleep 5;
sudo systemctl restart systemd-timesyncd.service
sleep 5;
sudo hwclock -w
sleep 1;
sudo hwclock --rtc /dev/rtc1 -w
sleep 1;
python3 ~/flash-tv-scripts/python_scripts/set_ext_ds3231_from_dt_now.py
set_correctly=$?

if [ $set_correctly -eq 1 ]; then
	zenity --warning --text="Exiting the code since the external RTC time was unable to be set. Please check it and restart the script."
	exit 1
fi

# Disable and stop currently running services
bash -x ~/flash-tv-scripts/services/stop_services.sh

# Copy, load, and enable services
sudo cp ~/flash-tv-scripts/services/flash-run-on-boot.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/services/flash-periodic-restart.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/services/homeassistant-run-on-boot.service /etc/systemd/system

sudo systemctl daemon-reload
