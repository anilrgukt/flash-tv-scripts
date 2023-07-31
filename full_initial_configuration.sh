#!/bin/bash

# Set to exit on non-zero error code
set -e

# Run all setup files
bash -x ~/flash-tv-scripts/setup_scripts/id_setup.sh
bash -x ~/flash-tv-scripts/setup_scripts/file_setup.sh
bash -x ~/flash-tv-scripts/setup_scripts/service_setup.sh
bash -x ~/flash-tv-scripts/install_scripts/full_install.sh

# Set up RTC again just in case
sudo sed -i 's/ATTR{hctosys}=="1"/ATTR{hctosys}=="0"/g' /lib/udev/rules.d/50-udev-default.rules 
sudo hwclock -w
