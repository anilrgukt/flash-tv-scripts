#!/bin/bash
# FILE setup
read -p 'Enter FLASH device ID (3 digits):' deviceID
read -p 'Enter family ID (3 digits probably):' familyID

# Create data directory
mkdir "~/data"
mkdir "$~/data/{familyID}${deviceID}_data"

# Replace device and family ID placeholders with input
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/flash-periodic-restart.service
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/flash-periodic-restart.service
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/flash_periodic_restart.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/flash_periodic_restart.sh
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/flash-run-on-boot.service
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/flash-run-on-boot.service
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/flash_run_on_boot.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/flash_run_on_boot.sh
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/homeassistant-run-on-boot.service
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/homeassistant-run-on-boot.service
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/sh_scripts/data_details.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/sh_scripts/data_details.sh

# Set up RTC
sudo sed -i 's/ATTR{hctosys}=="1"/ATTR{hctosys}=="0"/g' /lib/udev/rules.d/50-udev-default.rules 
sudo hwclock -w

# Copy, load, and enable services
sudo cp ~/flash-tv-scripts/flash-run-on-boot.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/flash-periodic-restart.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/homeassistant-run-on-boot.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable flash-periodic-restart.service
sudo systemctl enable flash-run-on-boot.service
sudo systemctl enable homeassistant-run-on-boot.service

# Remove video capture folder just in case as it's unnecessary for Jetsons
rm -r ~/flash-tv-scripts/video_capture

#from /harddisk/FLASH_TV_installation

#FLASH_TV ----> in /home/$USER
cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/FLASH_TV /home/$USER
#gaze_models ----> in /home/$USER
cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/gaze_models /home/$USER
#insightface ---> in /home/$USER
cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/insightface /home/$USER

#hidden files see (use ctrl+h for ubuntu to see them)
#.insightface ---> in /home/$USER
cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/.insightface /home/$USER
#.insightface ---> in /root
sudo cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/.insightface /root

#FLASH_TV_v2 ----> in /home/$USER/Desktop
cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/FLASH_TV_v2 ~/Desktop
#FLASH_TV_v3 ----> in /home/$USER/Desktop
cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/FLASH_TV_v3 ~/Desktop
