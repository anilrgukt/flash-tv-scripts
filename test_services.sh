#!/bin/bash

sudo systemctl start flash-periodic-restart.service
sudo systemctl start flash-run-on-boot.service
sudo systemctl start homeassistant-run-on-boot.service
sudo systemctl status flash-periodic-restart.service
sudo systemctl status flash-run-on-boot.service
sudo systemctl status homeassistant-run-on-boot.service
