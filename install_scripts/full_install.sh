#!/bin/bash

bash -x ~/flash-tv-scripts/install_scripts/flash_install.sh
bash -x ~/flash-tv-scripts/install_scripts/homeassistant_install.sh

sudo apt-get update
sudo apt-get dist-upgrade -y
