#!/bin/bash

set -e

bash -x ~/flash-tv-scripts/setup_scripts/ID_setup.sh 0
bash -x ~/flash-tv-scripts/setup_scripts/file_setup.sh
bash -x ~/flash-tv-scripts/setup_scripts/service_setup.sh
bash -x ~/flash-tv-scripts/install_scripts/full_install.sh
bash -x ~/flash-tv-scripts/setup_scripts/USB_backup_setup.sh
bash -x ~/flash-tv-scripts/setup_scripts/RTC_setup.sh
