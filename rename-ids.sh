#!/bin/bash

echo 'Enter FLASH device ID (3 digits):'
read devID
echo 'Enter family ID (probably 3 digits):'
read famID

sudo sed -i "s/XXX/$devID/g" ~/flash-tv-scripts/flash-periodic-restart.service
sudo sed -i "s/123/$famID/g" ~/flash-tv-scripts/flash-periodic-restart.service
sudo sed -i "s/XXX/$devID/g" ~/flash-tv-scripts/flash-periodic-restart.sh
sudo sed -i "s/123/$famID/g" ~/flash-tv-scripts/flash-periodic-restart.sh
sudo sed -i "s/XXX/$devID/g" ~/flash-tv-scripts/flash-run-on-boot.service
sudo sed -i "s/123/$famID/g" ~/flash-tv-scripts/flash-run-on-boot.service
sudo sed -i "s/XXX/$devID/g" ~/flash-tv-scripts/homeassistant-run-on-boot.service
sudo sed -i "s/123/$famID/g" ~/flash-tv-scripts/homeassistant-run-on-boot.service
sudo sed -i "s/XXX/$devID/g" ~/flash-tv-scripts/sh_scripts/data_details.sh
sudo sed -i "s/123/$famID/g" ~/flash-tv-scripts/sh_scripts/data_details.sh
