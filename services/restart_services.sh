#!/bin/bash

if [ $# -ge 1 ]; then
    USERNAME="$1"
else
    USERNAME="${SUDO_USER:-$USER}"
fi

sudo systemctl restart flash-periodic-restart.service
sleep 1;
sudo systemctl restart flash-run-on-boot.service
sleep 1;

cd "/home/${USERNAME}/homeassistant-compose" || exit
docker compose restart

sudo systemctl status --no-pager flash-periodic-restart.service flash-run-on-boot.service
