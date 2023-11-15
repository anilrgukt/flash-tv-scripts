#!/bin/bash

export username=flashsysXXX
export famId=123XXX

# Set up rtc0 (PSEQ_RTC) as the main interal RTC instead of rtc1 (tegra-RTC)
sudo sed -i 's/ATTR{hctosys}=="1"/ATTR{hctosys}=="0"/g' /lib/udev/rules.d/50-udev-default.rules

source ~/py38/bin/activate

sudo timedatectl set-ntp 1
sleep 5;

sudo systemctl restart systemd-timesyncd.service
sleep 5;

sudo hwclock -w && echo 'Internal RTC rtc0 (PSEQ_RTC, being used) was set' || (zenity --warning --text="Exiting the code since the internal RTC rtc0 (PSEQ_RTC, being used) time was unable to be set. Please check it and restart the script." --width 500 --height 100)
sleep 1;

sudo hwclock --rtc /dev/rtc1 -w && echo "Internal RTC rtc1 (tegra-RTC, not being used) was set" || "Internal RTC rtc1 (tegra-RTC, not being used) was unable to be set"
sleep 1;

python3 ~/flash-tv-scripts/python_scripts/set_ext_RTC_and_save_start_date.py /home/${username}/data/${famId}_data/${famId}_start_date.txt
set_correctly=$?

if [ $set_correctly -eq 1 ]; then
	zenity --warning --text="Exiting the code since the external RTC time was unable to be set. Please check it and restart the script." --width 500 --height 100 
	exit 1
fi
