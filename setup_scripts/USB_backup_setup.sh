#!/bin/bash

if lsusb | grep "SanDisk Corp. Ultra Fit"
then

	usb_backup_password=$(zenity --entry --hide-text --width 500 --height 100 --text="Enter USB Backup Password:")

	encoded_password=`python3 ~/flash-tv-scripts/setup_scripts/check_and_encode_password.py $usb_backup_password`
	exit_code=$?

	if [ $exit_code -eq 1 ]; then
		zenity --warning --width 500 --height 100 --text="Exiting the code since the password was incorrect.\nPlease restart the script and try again."
		exit 1
	fi

	export BORG_PASSPHRASE="$encoded_password"

	echo "$encoded_password" > ~/flash-tv-scripts/setup_scripts/borg-passphrase-flashsys002.txt

	usb_path=`lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'`

	export BORG_REPO=$usb_path/Data_Backups_flashsys002

	borg init -v --encryption=repokey

	borg key export --paper :: > $usb_path/borg-encrypted-key-backup-flashsys002.txt
	borg key export --paper :: > ~/borg-encrypted-key-backup-flashsys002.txt
	borg key export --paper :: > ~/flash-tv-scripts/setup_scripts/borg-encrypted-key-backup-flashsys002.txt

else
	zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB was not connected.\nPlease connect the backup USB and try again."
	exit 1
fi
