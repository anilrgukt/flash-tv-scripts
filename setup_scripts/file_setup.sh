#!/bin/bash

INSTALL_PATH="/media/${USER}/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation"

cp -r "${INSTALL_PATH}/FLASH_TV" "${HOME}"
cp -r "${INSTALL_PATH}/gaze_models" "${HOME}"
cp -r "${INSTALL_PATH}/insightface" "${HOME}"

# Hidden files - use Ctrl+H in file explorer to see them
cp -r "${INSTALL_PATH}/.insightface" "${HOME}"
sudo cp -r "${INSTALL_PATH}/.insightface" "/root"

cp -r "${INSTALL_PATH}/FLASH_TV_v2" "${HOME}/Desktop"
cp -r "${INSTALL_PATH}/FLASH_TV_v3" "${HOME}/Desktop"

exit 0
