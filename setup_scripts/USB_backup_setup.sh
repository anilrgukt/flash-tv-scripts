#!/bin/bash

username=flashsysXXX
HOME_DIR="/home/${username}"
BORG_ENV_FILE="${HOME_DIR}/.flash_borg_env"

# shellcheck source=/dev/null
source "${HOME_DIR}/py38/bin/activate"

BACKUP_USB_VENDOR="$(python3 -c 'import importlib.util, sys; spec = importlib.util.spec_from_file_location("flash_tv_install_defaults", sys.argv[1]); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); print(module.BACKUP_USB_VENDOR)' "${HOME_DIR}/flash-tv-scripts/config/install_defaults.py")"
BACKUP_USB_LSBLK_PATTERN="${BACKUP_USB_VENDOR%% *}"

if lsusb | grep -Fq "${BACKUP_USB_VENDOR}"; then

	BACKUP_USB_BLOCK_ID=$(lsblk -J -l -o NAME,MODEL,TYPE,PKNAME | python3 -c 'import json, sys
vendor = sys.argv[1]
disk_name = ""
for device in json.load(sys.stdin).get("blockdevices", []):
    if device.get("type") == "disk" and vendor in (device.get("model") or ""):
        disk_name = device.get("name") or ""
    elif disk_name and device.get("type") == "part" and device.get("pkname") == disk_name:
        print(device.get("name") or "")
        break
' "${BACKUP_USB_LSBLK_PATTERN}")
	
	if [ -z "${BACKUP_USB_BLOCK_ID}" ]; then
	    zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB is not detected in lsblk.\nPlease reconnect the backup USB and try again."
	    exit 1
	fi

	BACKUP_USB_UUID=$(sudo blkid -o value -s UUID "/dev/${BACKUP_USB_BLOCK_ID}")
	
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
 
	sudo sed -i -e 's/noauto//' -e 's/ ,,/ /' -e 's/ ,/ /' -e 's/,,/,/' -e 's/, / /' "${FSTAB}"
 
	# Create temp file to store plaintext password without echoing it in terminal
	temp_file=$(mktemp)
	
	zenity --entry --hide-text --width 500 --height 100 --text="Enter USB Backup Password:" > "${temp_file}"
	
	# Send password to be checked and encoded
	encoded_password=$(python3 "${HOME_DIR}/flash-tv-scripts/python_scripts/check_and_encode_passphrase.py" "${temp_file}")
	exit_code=$?
	
	# Overwrite and destroy temp file
	shred -z -u "${temp_file}"

	if [ ${exit_code} -eq 1 ]; then
		zenity --warning --width 500 --height 100 --text="Exiting the code since the password was incorrect.\nPlease restart the script and try again."
		exit 1
	fi
	
	# Export and save encoded password as borg passphrase
	export BORG_PASSPHRASE="${encoded_password}"

	# Export and save borg repo path
	export BORG_REPO="${BACKUP_USB_MOUNT_PATH}/USB_Backup_Data_${username}"

	umask 077
	printf 'export BORG_PASSPHRASE=%q\nexport BORG_REPO=%q\n' "${BORG_PASSPHRASE}" "${BORG_REPO}" > "${BORG_ENV_FILE}"

	# Initialize borg repo
	borg init -v --encryption=repokey

	# Export borg encryption keys to multiple places for backup
	borg key export --paper :: > "${BACKUP_USB_MOUNT_PATH}/borg-encrypted-key-backup-${username}.txt"
	borg key export --paper :: > "${HOME_DIR}/borg-encrypted-key-backup-${username}.txt"
	borg key export --paper :: > "${HOME_DIR}/flash-tv-scripts/setup_scripts/borg-encrypted-key-backup-${username}.txt"

else
	zenity --warning --width 500 --height 100 --text="Exiting the code since the backup USB was not detected in lsusb.\nPlease reconnect the backup USB and try again."
	exit 1
fi
