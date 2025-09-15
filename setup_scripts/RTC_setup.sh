#!/bin/bash

export username=flashsysXXX
export participantID=123XXX

# Set up rtc0 (PSEQ_RTC) as the main internal RTC instead of rtc1 (tegra-RTC)
sudo sed -i 's/ATTR{hctosys}=="1"/ATTR{hctosys}=="0"/g' "/lib/udev/rules.d/50-udev-default.rules"

# shellcheck source=/dev/null
source "/home/${username}/py38/bin/activate"

# Set the time to update automatically
sudo timedatectl set-ntp 1
sleep 5

# Restart the timesync service to force it to sync
sudo systemctl restart systemd-timesyncd.service
sleep 5

# Attempt to set the first internal RTC (rtc0, PSEQ_RTC, being used as the backup RTC)
if sudo hwclock -w; then
    echo "Internal RTC rtc0 (PSEQ_RTC, being used) was set"
else
    zenity --warning --text="Exiting the code since the internal RTC rtc0 (PSEQ_RTC, being used) time was unable to be set. Please check it and restart the script." --width 500 --height 100
    exit 1
fi
sleep 1

# Attempt to set the second internal RTC (rtc1, tegra-RTC, not being used)
if sudo hwclock --rtc "/dev/rtc1" -w; then
    echo "Internal RTC rtc1 (tegra-RTC, not being used) was set"
else
    echo "Internal RTC rtc1 (tegra-RTC, not being used) was unable to be set"
fi
sleep 1

# Attempt to set the external RTC (DS3231, ZS-042, being used as the primary RTC)
START_DATE_FILE_PATH="/home/${username}/data/${participantID}_data/${participantID}_start_date.txt"
python3 "/home/${username}/flash-tv-scripts/python_scripts/set_external_RTC_and_save_start_date.py" "${START_DATE_FILE_PATH}"
external_RTC_set_correctly=$?

if [ "${external_RTC_set_correctly}" -eq 1 ]; then
	zenity --warning --text="Exiting the code since the external RTC time was unable to be set. Please check it and restart the script." --width 500 --height 100 
	exit 1
fi