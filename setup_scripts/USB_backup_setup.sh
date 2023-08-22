#!/bin/bash

usb_backup_password=$(zenity --entry --hide-text --width 500 --height 100 --text="Enter USB Backup Password:")

checked_password=`python3 ~/flash-tv-scripts/setup_scripts/password_check.py $usb_backup_password`
exit_code=$?

if [ $exit_code -eq 1 ]; then
	zenity --warning --width 500 --height 100 --text="Exiting the code since the password was incorrect.\nPlease restart the script and try again."
	exit 1
fi

export BORG_PASSPHRASE="$checked_password"

echo "$checked_password" > ~/flash-tv-scripts/setup_scripts/borg_passphrase.txt

usb_path=`lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'`

export BORG_REPO=$usb_path/flashsysXXX_Data_Backups

borg init -v --encryption=repokey

borg key export --paper :: > $usb_path/flashsysXXX-borg-encrypted-key-backup.txt
borg key export --paper :: > ~/flashsysXXX-borg-encrypted-key-backup.txt
borg key export --paper :: > ~/flash-tv-scripts/setup_scripts/flashsysXXX-borg-encrypted-key-backup.txt
