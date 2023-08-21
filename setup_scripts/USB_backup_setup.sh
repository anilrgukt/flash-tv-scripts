#!/bin/bash
read -p 'Enter USB Backup Password: ' usb_backup_password

checked_password=`zenity --entry --title="Verify USB Backup Password" --width 500 --height 100 --text="Please verify the USB backup password shown below by typing it again and clicking OK.\n\nClick Cancel if it is incorrect.\n\nUSB Backup Password: $usb_backup_password"`

user_resp=$?

if [ $user_resp -eq 1 ]; then
	zenity --warning --width 500 --height 100 --text="Exiting the code since the input was canceled.\nPlease restart the script and try again."
	exit 1
fi

if [ "$checked_password" != "$usb_backup_password" ]; then
	zenity --warning --width 500 --height 100 --text="Exiting the code since the second input of the password was not correct.\nPlease restart the script and try again."
	exit 2

fi

export BORG_PASSPHRASE="$checked_password"

usb_path=`lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'`

export BORG_REPO=$usb_path/flashsysXXX_Data_Backups

borg init -v --encryption=repokey

borg key export --paper :: > $usb_path/flashsysXXX-borg-encrypted-key-backup.txt
borg key export --paper :: > ~/flashsysXXX-borg-encrypted-key-backup.txt

#borg create ::{user}-FLASH-HA-Data-Backup-{now} ~/data ~/.homeassistant
