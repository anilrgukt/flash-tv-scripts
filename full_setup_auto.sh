#!/bin/bash

read -p 'Enable logging (y/n)?' answer
if [ "$answer" = "${answer#[Yy]}" ] ;then
    bash -x ~/flash-tv-scripts/FLASH_filesetup.sh
    bash -x ~/flash-tv-scripts/install_scripts/full_install_auto.sh
else
    bash ~/flash-tv-scripts/FLASH_filesetup.sh
    bash ~/flash-tv-scripts/install_scripts/full_install_auto.sh
fi




