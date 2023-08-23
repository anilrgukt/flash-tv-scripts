#!/bin/bash

if lsusb | grep "SanDisk Corp. Ultra Fit" &>/dev/null
then
	temp_file=$(mktemp)
	stty -echo
	
	zenity --entry --hide-text --width 500 --height 100 --text="Enter USB Backup Password:" > "$temp_file"
	
	encoded_password=`python3 ~/flash-tv-scripts/setup_scripts/check_and_encode_password.py "$temp_file"`
	exit_code=$?
	
	shred -z -u "$temp_file"

	stty echo
	
	if [ $exit_code -eq 1 ]; then
		zenity --warning --width 500 --height 100 --text="Exiting the code since the password was incorrect.\nPlease restart the script and try again."
		exit 1
	fi

	export BORG_PASSPHRASE="$encoded_password"

	echo "$encoded_password" > ~/flash-tv-scripts/setup_scripts/borg-passphrase-flashsysXXX.txt

	backup_usb_path=`lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'`

	export BORG_REPO=$backup_usb_path/USB_Backup_Data_flashsysXXX
	
	BORG_REPO_ENV_VAR="export BORG_REPO=\$backup_usb_path/USB_Backup_Data_flashsysXXX"
	FILE="~/.bashrc"
	grep -xqF -- "USB_Backup_Data_flashsys" "$FILE" || echo "$BORG_REPO_ENV_VAR" >> "$FILE"

	borg init -v --encryption=repokey

	borg key export --paper :: > $backup_usb_path/borg-encrypted-key-backup-flashsysXXX.txt
	borg key export --paper :: > ~/borg-encrypted-key-backup-flashsysXXX.txt
	borg key export --paper :: > ~/flash-tv-scripts/setup_scripts/borg-encrypted-key-backup-flashsysXXX.txt

else
	zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB was not connected.\nPlease connect the backup USB and try again."
	exit 1
fi
