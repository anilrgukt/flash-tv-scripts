#!/bin/bash
# FILE setup

# Set up RTC
sudo sed -i 's/ATTR{hctosys}=="1"/ATTR{hctosys}=="0"/g' /lib/udev/rules.d/50-udev-default.rules 
sudo hwclock -w

# from /harddisk/FLASH_TV_installation

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

# New Python scripts

cp -r ~/flash-tv-scripts/python_scripts/. ~/Desktop/FLASH_TV_v3
