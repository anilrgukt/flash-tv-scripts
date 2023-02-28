#!/bin/bash

read -p 'Enable logging (y/n)?' answer
if [ "$answer" = "${answer#[Yy]}" ] ;then
    bash -x ~/flash-tv-scripts/full_file_setup.sh
    bash -x ~/flash-tv-scripts/install_scripts/full_install.sh
else
    bash ~/flash-tv-scripts/full_file_setup.sh
    bash ~/flash-tv-scripts/install_scripts/full_install.sh
fi




