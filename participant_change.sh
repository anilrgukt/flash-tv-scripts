#!/bin/bash
# MUST DELETE AND RECLONE the flash-tv-scripts folder BEFORE RUNNING THIS OR IT WILL NOT WORK PROPERLY

# if [ ! -d ~/.homeassistant ]; then
# 	zenity --warning --text="Exiting the code since Home Assistant has not been set up.\n\nPlease set up Home Assistant before running this script." --width 500 --height 100
# 	exit 1
# fi

if [ ! -d ~/docker-compose/ha-config ]; then
	zenity --warning --text="Exiting the code since Home Assistant has not been set up.\n\nPlease set up Home Assistant before running this script." --width 500 --height 100
	exit 1
fi

skip_checking=0

# Handling command-line arguments
if [ "$#" -ne 3 ] && [ "$#" -ne 4 ] && [ "$#" -ne 5 ]; then
	if [ "$#" -eq 4 ]; then
		plugID=$1
		deviceID=$2
		familyID=$3
		skip_checking=$4
	elif [ "$#" -eq 5 ]; then
		plugID=$1
		deviceID=$2
		familyID=$3
		mac_address=$4
		skip_checking=$5
	else
		# Prompt user for plugID, deviceID, familyID, and MAC address
		echo "Command Line Usage: $0 (plugID) (deviceID) (familyID) (mac_address)"
		
		# Setting up plug ID for Home Assistant config file
		plugID=$(zenity --entry --width 500 --height 100 --text="Enter Zigbee plug ID index from Home Assistant or YYYY (uppercase) if the plug is not ready:")
		
		deviceID=$(zenity --entry --width 500 --height 100 --text="Enter FLASH device ID (3 digits):")
		
		familyID=$(zenity --entry --width 500 --height 100 --text="Enter family ID (P1-1XXX for TECH):")
		
		# New input for MAC address
		mac_address=$(zenity --entry --width 500 --height 100 --text="Enter the MAC address (format: XX:XX:XX:XX:XX:XX):")
	fi
else
	plugID=$1
	deviceID=$2
	familyID=$3
	mac_address=$4
fi

if [ $skip_checking -ne 1 ]; then
	zenity --question --title="Verify Plug ID, Device ID, Family ID, and MAC Address" --width 500 --height 100 --text="Please verify the following details\n\nPlug ID: $plugID\nFamily ID: ${familyID}\nDevice ID: ${deviceID}\nMAC Address: ${mac_address}" --no-wrap
	user_resp=$?
	
	if [ ${user_resp} -eq 1 ]; then
		zenity --warning --text="Exiting the code since the plug ID, device ID, family ID, or MAC address were not entered correctly according to the user. Please restart the script to try again." --width 500 --height 100
		exit 1
	fi
fi

# Function to validate MAC address format (XX:XX:XX:XX:XX:XX)
validate_mac_address() {
    local mac=$1
    # Check if MAC address has exactly 6 pairs of hexadecimal digits separated by colons
    if [[ $mac =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
        return 0  # Valid MAC address
    else
        return 1  # Invalid MAC address
    fi
}

# Validate the MAC address format
if ! validate_mac_address "$mac_address"; then
    zenity --warning --text="The MAC address format is invalid. Please enter a valid MAC address in the format XX:XX:XX:XX:XX:XX." --width 500 --height 100
    exit 1
fi

# Update the target MAC address in the C code
sed -i "s/ZZZZ/$mac_address/g" ~/flash-tv-scripts/services/bt_beacon_accelerometer_scanner.c

# Set to exit on non-zero error code
set -e

# Update the configuration.yaml with the plug ID
sed -i "s/YYYY/$plugID/g" ~/flash-tv-scripts/install_scripts/configuration.yaml

bash -x ~/flash-tv-scripts/setup_scripts/ID_setup.sh $deviceID $familyID 1
sleep 1;

bash -x ~/flash-tv-scripts/setup_scripts/USB_backup_setup.sh $skip_checking
sleep 1;

bash -x ~/flash-tv-scripts/setup_scripts/service_setup.sh
sleep 1;

bash -x ~/flash-tv-scripts/setup_scripts/RTC_setup.sh
sleep 1;

# Copy modified configuration.yaml with plug ID to Home Assistant folder after updating the family and device IDs as well
#cp ~/flash-tv-scripts/install_scripts/configuration.yaml ~/.homeassistant
sudo cp /home/flashsys${deviceID}/flash-tv-scripts/install_scripts/configuration.yaml /home/flashsys${deviceID}/docker-compose/ha-config/configuration.yaml

cd ~/docker-compose/ha-config
docker compose up -d

# Copy git config into data folder
cp ~/flash-tv-scripts/.git/config ~/data/${familyID}${deviceID}_data/git_config.txt
