read -p 'Enter FLASH device ID (3 digits):' deviceID
read -p 'Enter family ID (3 digits probably):' familyID

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
sed -i "s/XXX/$deviceID/g" ~/flash-tv-scripts/sh_scripts/data_details.sh
sed -i "s/123/$familyID/g" ~/flash-tv-scripts/sh_scripts/data_details.sh
