#!/bin/bash

# Set up RTC
sudo sed -i 's/ATTR{hctosys}=="1"/ATTR{hctosys}=="0"/g' /lib/udev/rules.d/50-udev-default.rules

source ~/py38/bin/activate

timedatectl set-ntp 1
sleep 5;

sudo systemctl restart systemd-timesyncd.service
sleep 5;

if [[ $(sudo hwclock -w 1>/dev/null) ]]; then
	zenity --warning --text="Exiting the code since the internal RTC time was unable to be set. Please check it and restart the script." --width 500 --height 100 
	exit 1
fi
sleep 1;

if [[ $(sudo hwclock --rtc /dev/rtc1 -w 1>/dev/null) ]]; then
	echo "rtc1 was unable to be set"
fi
sleep 1;

python3 ~/flash-tv-scripts/python_scripts/set_ext_ds3231_from_dt_now.py
set_correctly=$?

if [ $set_correctly -eq 1 ]; then
	zenity --warning --text="Exiting the code since the external RTC time was unable to be set. Please check it and restart the script." --width 500 --height 100 
	exit 1
fi

# Disable and stop currently running services
bash -x ~/flash-tv-scripts/services/stop_services.sh

# Copy, load, and enable services
sudo cp ~/flash-tv-scripts/services/flash-run-on-boot.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/services/flash-periodic-restart.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/services/homeassistant-run-on-boot.service /etc/systemd/system

sudo systemctl daemon-reload
