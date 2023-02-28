#!/bin/bash

# Take input
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
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/runtime_scripts/data_details.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/runtime_scripts/data_details.sh
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/install_scripts/configuration.yaml
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/install_scripts/configuration.yaml

