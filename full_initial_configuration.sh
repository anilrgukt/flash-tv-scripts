#!/bin/bash

# Set to exit on non-zero error code
set -e

# Run all setup files
bash -x ~/flash-tv-scripts/setup_scripts/id_setup.sh
bash -x ~/flash-tv-scripts/setup_scripts/file_setup.sh
bash -x ~/flash-tv-scripts/setup_scripts/service_setup.sh
bash -x ~/flash-tv-scripts/install_scripts/full_install.sh
bash -x ~/flash-tv-scripts/setup_scripts/RTC_setup.sh
