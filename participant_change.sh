#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

# Setting up plug ID for Home Assistant config file
read -p 'Enter plug ID (4 characters lowercase) or YYYY (uppercase) if the plug is not yet ready:' plugID

sed -i "s/YYYY/$plugID/g" ~/flash-tv-scripts/install_scripts/configuration.yaml

# Copying the config file to the Home Assistant directory
cp ~/flash-tv-scripts/install_scripts/configuration.yaml ~/.homeassistant

bash -x ~/flash-tv-scripts/setup_scripts/id_setup.sh
bash -x ~/flash-tv-scripts/setup_scripts/service_setup.sh


