sudo cp ~/flash-tv-scripts/flash-run-on-boot.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/flash-periodic-restart.service /etc/systemd/system
sudo cp ~/flash-tv-scripts/homeassistant-run-on-boot.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable flash-periodic-restart.service
sudo systemctl enable flash-run-on-boot.service
sudo systemctl enable homeassistant-run-on-boot.service
sudo systemctl start flash-periodic-restart.service
sudo systemctl start flash-run-on-boot.service
sudo systemctl start homeassistant-run-on-boot.service

