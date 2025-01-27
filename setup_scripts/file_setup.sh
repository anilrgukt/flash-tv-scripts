#!/bin/bash
### File Setup ###

# from /harddisk/FLASH_TV_installation

# FLASH_TV ----> in /home/flashsysXXX
cp -r "/media/${USER}/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/FLASH_TV" "${HOME}"

# gaze_models ----> in /home/flashsysXXX
cp -r "/media/${USER}/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/gaze_models" "${HOME}"

# insightface ---> in /home/flashsysXXX
cp -r "/media/${USER}/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/insightface" "${HOME}"

# Hidden files, use Ctrl+H in the file explorer (Nautilus) to see them

# .insightface ---> in /home/flashsysXXX
cp -r "/media/${USER}/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/.insightface" "${HOME}"

# .insightface ---> in /root
sudo cp -r "/media/${USER}/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/.insightface" "/root"

# FLASH_TV_v2 ----> in /home/flashsysXXX/Desktop
cp -r "/media/${USER}/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/FLASH_TV_v2" "${HOME}/Desktop"

# FLASH_TV_v3 ----> in /home/flashsysXXX/Desktop
cp -r "/media/${USER}/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/FLASH_TV_v3" "${HOME}/Desktop"

exit 0
