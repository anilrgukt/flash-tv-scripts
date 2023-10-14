#!/bin/bash

if [ ! `lsusb | grep -q "SanDisk Corp. Ultra Fit"` ]; then

	backup_usb_block_id=$(lsblk -o NAME,MODEL | grep -A 1 SanDisk | awk '/SanDisk/{getline; gsub("└─", ""); print}')
	
	if [ -z "$backup_usb_block_id" ]; then
	    zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB is not detected in lsblk.\nPlease reconnect the backup USB and try again."
	    exit 1
	fi

 	backup_usb_uuid=$(sudo blkid -t TYPE=vfat -sUUID | grep ${backup_usb_block_id} | cut -d '"' -f2)
	
	if [ -z "$backup_usb_uuid" ]; then
	    zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB is not detected in blkid.\nPlease reconnect the backup USB and try again."
	    exit 1
	fi
      
	# Enable automounting of the USB on boot (disabled by default)
 	FSTAB=/etc/fstab

  	backup_usb_mount_path=/home/media/${backup_usb_uuid}

 	backup_usb_fstab_line="UUID=${backup_usb_uuid} /home/media/${backup_usb_uuid} auto uid=${UID},gid=${UID} 0 0"

 	grep -q '.*UUID=.* /home/media/.* auto uid=.*,gid=.* 0 0.*' "${FSTAB}" || echo "${backup_usb_fstab_line}" | sudo tee -a "${FSTAB}"
  	sudo sed -i "s@.*UUID=.* /home/media/.* auto uid=.*,gid=.* 0 0.*@${backup_usb_fstab_line}@" "${FSTAB}"
 
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
	
	BASHRC=/home/flashsysXXX/.bashrc

	# Export and save encoded password as borg passphrase
	export BORG_PASSPHRASE="${encoded_password}"
	
	echo "${encoded_password}" > /home/flashsysXXX/flash-tv-scripts/setup_scripts/borg-passphrase-flashsysXXX.txt
	
	BORG_PASSPHRASE_EXPORT="export BORG_PASSPHRASE="${encoded_password}""

	grep -q '.*BORG_PASSPHRASE.*' "${BASHRC}" || echo "${BORG_PASSPHRASE_EXPORT}" >> "${BASHRC}"
	sed -i "s@.*BORG_PASSPHRASE.*@${BORG_PASSPHRASE_EXPORT}@" "${BASHRC}"

	# Export and save borg repo path
	export BORG_REPO=${backup_usb_mount_path}/USB_Backup_Data_flashsysXXX
	
	BORG_REPO_EXPORT="export BORG_REPO=${backup_usb_mount_path}/USB_Backup_Data_flashsysXXX"
	
	grep -q '.*BORG_REPO.*' "${BASHRC}" || echo "${BORG_REPO_EXPORT}" >> "${BASHRC}"
	sed -i "s@.*BORG_REPO.*@${BORG_REPO_EXPORT}@" "${BASHRC}"

	# Initialize borg repo
	borg init -v --encryption=repokey

	# Export borg encryption keys to multiple places for backup
	borg key export --paper :: > ${backup_usb_mount_path}/borg-encrypted-key-backup-flashsysXXX.txt
	borg key export --paper :: > /home/flashsysXXX/borg-encrypted-key-backup-flashsysXXX.txt
	borg key export --paper :: > /home/flashsysXXX/flash-tv-scripts/setup_scripts/borg-encrypted-key-backup-flashsysXXX.txt

else
	zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB was not detected in lsusb.\nPlease reconnect the backup USB and try again."
	exit 1
fi
