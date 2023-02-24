#!/bin/bash
# FILE setup

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

#flash-run-on-boot.service ---> in /home/$USER/Desktop
#cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/flash-run-on-boot.service ~/Desktop
#flash-run_on_boot.sh ----> in /home/$USER/Desktop
#cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/flash_run_on_boot.sh ~/Desktop


#build_gallery.sh ----> in /home/$USER/Desktop
#cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/build_gallery.sh ~/Desktop
#create_faces.sh ----> in /home/$USER/Desktop
#cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/create_faces.sh ~/Desktop
#run_flashtv_system.sh ----> in /home/$USER/Desktop
#cp -r /media/$USER/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/run_flashtv_system.sh ~/Desktop
