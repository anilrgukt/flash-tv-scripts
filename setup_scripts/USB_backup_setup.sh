#!/bin/bash

if [ ! `lsusb | grep -q "SanDisk Corp. Ultra Fit"` ]; then

	if [ `lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'` ]; then
 
 		backup_usb_path=`lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'`

	elif [ `lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep /mnt/usb | awk '{print $2}'` ]; then
 
 		backup_usb_path=`lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep /mnt/usb | awk '{print $2}'`
   
    	else
     
     		zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB is not mounted.\nPlease mount the backup USB and try again."
		exit 1

  	fi
     		
	# Enable automounting of the USB on boot (disabled by default)
 	sudo sed -i /etc/fstab -e 's/noauto//' -e 's/ ,,/ /' -e 's/ ,/ /' -e 's/,,/,/' -e 's/, / /'
 
	# Create temp file to store plaintext password without echoing it in terminal
	temp_file=$(mktemp)
	
	zenity --entry --hide-text --width 500 --height 100 --text="Enter USB Backup Password:" > "${temp_file}"
	
	# Send password to be checked and encoded using cryptography modules in Python
	encoded_password=`python3 /home/flashsysXXX/flash-tv-scripts/python_scripts/check_and_encode_password.py "${temp_file}"`
	exit_code=$?
	
	# Overwrite and destroy temp file
	shred -z -u "${temp_file}"

	if [ ${exit_code} -eq 1 ]; then
		zenity --warning --width 500 --height 100 --text="Exiting the code since the password was incorrect.\nPlease restart the script and try again."
		exit 1
	fi
	
	FILE=/home/flashsysXXX/.bashrc

	# Export and save encoded password as borg passphrase
	export BORG_PASSPHRASE="${encoded_password}"
	
	echo "${encoded_password}" > /home/flashsysXXX/flash-tv-scripts/setup_scripts/borg-passphrase-flashsysXXX.txt
	
	BORG_PASSPHRASE_EXPORT="export BORG_PASSPHRASE="${encoded_password}""

	grep -q '.*BORG_PASSPHRASE.*' "${FILE}" || echo "${BORG_PASSPHRASE_EXPORT}" >> "${FILE}"
	sed -i "s@.*BORG_PASSPHRASE.*@${BORG_PASSPHRASE_EXPORT}@" "${FILE}"

	# Export and save borg repo path
	export BORG_REPO=${backup_usb_path}/USB_Backup_Data_flashsysXXX
	
	BORG_REPO_EXPORT="export BORG_REPO=${backup_usb_path}/USB_Backup_Data_flashsysXXX"
	
	grep -q '.*BORG_REPO.*' "${FILE}" || echo "${BORG_REPO_EXPORT}" >> "${FILE}"
	sed -i "s@.*BORG_REPO.*@${BORG_REPO_EXPORT}@" "${FILE}"

	# Initialize borg repo
	borg init -v --encryption=repokey

	# Export borg encryption keys to multiple places for backup
	borg key export --paper :: > ${backup_usb_path}/borg-encrypted-key-backup-flashsysXXX.txt
	borg key export --paper :: > /home/flashsysXXX/borg-encrypted-key-backup-flashsysXXX.txt
	borg key export --paper :: > /home/flashsysXXX/flash-tv-scripts/setup_scripts/borg-encrypted-key-backup-flashsysXXX.txt

else
	zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB is not connected.\nPlease connect the backup USB and try again."
	exit 1
fi
