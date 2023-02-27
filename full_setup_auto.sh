#!/bin/bash

bash -x ~/flash-tv-scripts/rename-ids.sh &
bash -x ~/flash-tv-scripts/FLASH_filesetup.sh &
bash -x ~/flash-tv-scripts/install_scripts/full_install_auto.sh &
wait
