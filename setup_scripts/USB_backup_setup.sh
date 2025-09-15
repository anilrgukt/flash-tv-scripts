#!/bin/bash

username=flashsysXXX

# shellcheck source=/dev/null
source "${HOME}/py38/bin/activate"

if lsusb | grep -q "SanDisk Corp. Ultra Fit"; then

	BACKUP_USB_BLOCK_ID=$(lsblk -o NAME,MODEL | grep -A 1 SanDisk | awk '/SanDisk/{getline; gsub("└─", ""); print}')
	
	if [ -z "${BACKUP_USB_BLOCK_ID}" ]; then
	    zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB is not detected in lsblk.\nPlease reconnect the backup USB and try again."
	    exit 1
	fi

 	# shellcheck disable=SC2086
	# Must use unquoted variable for some reason
 	BACKUP_USB_UUID=$(sudo blkid -t TYPE=vfat -sUUID | grep ${BACKUP_USB_BLOCK_ID} | cut -d '"' -f2)
	
	if [ -z "${BACKUP_USB_UUID}" ]; then
	    zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB is not detected in blkid.\nPlease reconnect the backup USB and try again."
	    exit 1
	fi
      
	# Enable automounting of the USB on boot (disabled by default)
 	FSTAB=/etc/fstab

  	BACKUP_USB_MOUNT_PATH="/media/${username}/${BACKUP_USB_UUID}"

 	BACKUP_USB_FSTAB_LINE="UUID=${BACKUP_USB_UUID} /media/${username}/${BACKUP_USB_UUID} auto uid=${UID},gid=${UID} 0 0"

 	grep -q ".*UUID=.* /media/${username}/.* auto uid=.*,gid=.* 0 0.*" "${FSTAB}" || echo "${BACKUP_USB_FSTAB_LINE}" | sudo tee -a "${FSTAB}"
  	sudo sed -i "s@.*UUID=.* /media/${username}/.* auto uid=.*,gid=.* 0 0.*@${BACKUP_USB_FSTAB_LINE}@" "${FSTAB}"
 
 	sudo sed -i /etc/fstab -e 's/noauto//' -e 's/ ,,/ /' -e 's/ ,/ /' -e 's/,,/,/' -e 's/, / /'
 
	# Create temp file to store plaintext password without echoing it in terminal
	temp_file=$(mktemp)
	
	zenity --entry --hide-text --width 500 --height 100 --text="Enter USB Backup Password:" > "${temp_file}"
	
	# Send password to be checked and encoded
	encoded_password=$(python3 "/home/${username}/flash-tv-scripts/python_scripts/check_and_encode_passphrase.py" "${temp_file}")
	exit_code=$?
	
	# Overwrite and destroy temp file
	shred -z -u "${temp_file}"

	if [ ${exit_code} -eq 1 ]; then
		zenity --warning --width 500 --height 100 --text="Exiting the code since the password was incorrect.\nPlease restart the script and try again."
		exit 1
	fi
	
	BASHRC=/home/${username}/.bashrc

	# Export and save encoded password as borg passphrase
	export BORG_PASSPHRASE="${encoded_password}"
		
	borg_passphrase_export_line="export BORG_PASSPHRASE=${encoded_password}"

	grep -q '.*BORG_PASSPHRASE.*' "${BASHRC}" || echo "${borg_passphrase_export_line}" >> "${BASHRC}"
	sed -i "s@.*BORG_PASSPHRASE.*@${borg_passphrase_export_line}@" "${BASHRC}"

	# Export and save borg repo path
	export BORG_REPO="${BACKUP_USB_MOUNT_PATH}/USB_Backup_Data_${username}"
	
	borg_repo_export_line="export BORG_REPO='${BACKUP_USB_MOUNT_PATH}/USB_Backup_Data_${username}'"
	
	grep -q '.*BORG_REPO.*' "${BASHRC}" || echo "${borg_repo_export_line}" >> "${BASHRC}"
	sed -i "s@.*BORG_REPO.*@${borg_repo_export_line}@" "${BASHRC}"

	# Comment out line in .bashrc preventing running in non-interactive shells so that it can be sourced from a script
	sed -i '/^case $- in/,/^esac/s/^/#/' "${BASHRC}"

	# Initialize borg repo
	borg init -v --encryption=repokey

	# Export borg encryption keys to multiple places for backup
	borg key export --paper :: > "${BACKUP_USB_MOUNT_PATH}/borg-encrypted-key-backup-${username}.txt"
	borg key export --paper :: > "/home/${username}/borg-encrypted-key-backup-${username}.txt"
	borg key export --paper :: > "/home/${username}/flash-tv-scripts/setup_scripts/borg-encrypted-key-backup-${username}.txt"

else
	zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB was not detected in lsusb.\nPlease reconnect the backup USB and try again."
	exit 1
fi
