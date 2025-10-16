#!/bin/bash

if [ $# -ge 1 ]; then
    USERNAME="$1"
else
    USERNAME="${SUDO_USER:-$USER}"
fi

sudo systemctl stop flash-periodic-restart.service
sleep 1;
sudo systemctl stop flash-run-on-boot.service
sleep 1;

sudo systemctl disable flash-periodic-restart.service
sleep 1;
sudo systemctl disable flash-run-on-boot.service

cd "/home/${USERNAME}/homeassistant-compose" || exit
docker compose down
