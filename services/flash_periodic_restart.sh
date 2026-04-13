#!/bin/bash

export participant_id=123XXX
export username=flashsysXXX
export LOG_FOLDER_PATH="/home/${username}/data/${participant_id}_data/logs"
export BACKUP_DIRS="/home/${username}/data /home/${username}/homeassistant-compose/config"

mkdir -p "${LOG_FOLDER_PATH}"

# Activate Python 3.8 virtual environment with libraries set up
source "/home/${username}/py38/bin/activate"

# Run the script for checking folder file updates in the background for various folders
python3 "/home/${username}/flash-tv-scripts/python_scripts/check_file_events.py" ${participant_id} "${LOG_FOLDER_PATH}" "/home/${username}/data/${participant_id}_data/${participant_id}_varlog_filesequence.csv" &
python3 "/home/${username}/flash-tv-scripts/python_scripts/check_file_events.py" ${participant_id} "/home/${username}/data/${participant_id}_data" "/home/${username}/data/${participant_id}_data/${participant_id}_flashlog_filesequence.csv" &

# Run the tegrastats command and output it every 30 seconds to a log file in the background
tegrastats --interval 30000 --logfile "/home/${username}/data/${participant_id}_data/${participant_id}_tegrastats.log" &

# Run the script for checking for FLASH camera warnings in the background 
bash "/home/${username}/flash-tv-scripts/services/flash_check_camera_warnings.sh" ${participant_id} ${username} &

# Run the script for reading and saving the data from the Bluetooth beacon accelerometer in the background
#bash "/home/${username}/flash-tv-scripts/services/run_bluetooth_beacon_accelerometer_data_reader.sh" ${username} &

# Get the amount of time to sleep before starting the rest of the script from the FLASH run on boot service delay (accounts for the time to update when rebooting)
FLASH_RUN_ON_BOOT_SERVICE_PATH="/home/${username}/flash-tv-scripts/services/flash-run-on-boot.service"

sleep_interval=$(grep -oP '(?<=ExecStartPre=/bin/sleep )\d+' "${FLASH_RUN_ON_BOOT_SERVICE_PATH}")

sleep "${sleep_interval}";

# Get the current amount of times the device has rebooted
REBOOT_INDEX_PATH="/home/${username}/data/${participant_id}_data/${participant_id}_reboot_index.txt"

if [ -e "${REBOOT_INDEX_PATH}" ]; then

    last_line=$(tail -n 1 "${REBOOT_INDEX_PATH}")
    
    last_index=$(echo "${last_line}" | awk '{print $NF}')
    
    new_index=$((last_index + 1))
    
else

    new_index=1
    
fi

datetime_for_index=$(date +"%d_%b_%Y_%H-%M-%S_%Z")

echo "flash_periodic_restart.sh was just restarted around ${datetime_for_index}, implying that the current reboot index is: ${new_index}" >> "${REBOOT_INDEX_PATH}"

# Run the periodic restart loop
loop=1
while true;
do
	sleep 21600; # 6 hours
	 
	datetime=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	
	mkdir -p "${LOG_FOLDER_PATH}/varlogs_${datetime}"

	# Output various statuses
	echo "Reboot Index: ${new_index}" >> "${LOG_FOLDER_PATH}/varlogs_${datetime}/log_${datetime}.txt"
	echo "Reboot Index: ${new_index}" >> "${LOG_FOLDER_PATH}/varlogs_${datetime}/logend_${datetime}.txt"
	echo "Reboot Index: ${new_index}" >> "${LOG_FOLDER_PATH}/varlogs_${datetime}/timedate_${datetime}.txt"

	systemctl status flash-run-on-boot.service >> "${LOG_FOLDER_PATH}/varlogs_${datetime}/log_${datetime}.txt"
	systemctl status flash-run-on-boot.service >> "${LOG_FOLDER_PATH}/varlogs_${datetime}/logend_${datetime}.txt"
	
	python3 /home/${username}/flash-tv-scripts/python_scripts/update_or_check_system_time_from_RTCs.py "check" "/home/${username}/data/${participant_id}_data/${participant_id}_start_date.txt" >> "${LOG_FOLDER_PATH}/varlogs_${datetime}/timedate_${datetime}.txt"	
	v4l2-ctl --list-devices > "${LOG_FOLDER_PATH}/varlogs_${datetime}/camera_${datetime}.txt"
	echo -e "\nLogitech Camera iSerial Number: $(sudo lsusb -v -d 046d: 2>/dev/null | grep -i serial | awk '{print substr($0, length($0)-7)}')" >> "${LOG_FOLDER_PATH}/varlogs_${datetime}/camera_${datetime}.txt"

	# Stop the FLASH run on boot service
	systemctl stop flash-run-on-boot.service
	
	# Make sure that all instances of the FLASH script are destroyed
	pkill -9 -f run_flash_data_collection.py
	
	# Backup logs
	mv "/home/${username}/data/${participant_id}_data/${participant_id}_flash_logstdout.log" "/home/${username}/data/${participant_id}_data/${participant_id}_flash_logstderr.log" "${LOG_FOLDER_PATH}/varlogs_${datetime}"
	cp "/home/${username}/data/${participant_id}_data/${participant_id}_flash_logstdoutp.log" "/home/${username}/data/${participant_id}_data/${participant_id}_flash_logstderrp.log" "${LOG_FOLDER_PATH}/varlogs_${datetime}"
 
	# Backup files to the USB, not including faces
	BORG_CHECK_TIMEOUT="15m"
	BORG_REPAIR_TIMEOUT="30m"
	BORG_CREATE_TIMEOUT="2h"
	BORG_PRUNE_TIMEOUT="30m"
	BACKUP_USB_VENDOR="$(python3 -c 'import importlib.util, sys; spec = importlib.util.spec_from_file_location("flash_tv_install_defaults", sys.argv[1]); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); print(module.BACKUP_USB_VENDOR)' "/home/${username}/flash-tv-scripts/config/install_defaults.py")"
	BACKUP_USB_LSBLK_PATTERN="${BACKUP_USB_VENDOR%% *}"
	BACKUP_USB_BLOCK_ID=""
	BACKUP_USB_UUID=""
	BACKUP_USB_MOUNT_PATH=""

	if lsusb | grep -Fq "${BACKUP_USB_VENDOR}"; then
		BACKUP_USB_BLOCK_ID="$(lsblk -J -l -o NAME,MODEL,TYPE,PKNAME | python3 -c 'import json, sys
vendor = sys.argv[1]
disk_name = ""
for device in json.load(sys.stdin).get("blockdevices", []):
    if device.get("type") == "disk" and vendor in (device.get("model") or ""):
        disk_name = device.get("name") or ""
    elif disk_name and device.get("type") == "part" and device.get("pkname") == disk_name:
        print(device.get("name") or "")
        break
' "${BACKUP_USB_LSBLK_PATTERN}")"

		if [ -n "${BACKUP_USB_BLOCK_ID}" ]; then
			BACKUP_USB_UUID="$(sudo blkid -t TYPE=vfat -sUUID "/dev/${BACKUP_USB_BLOCK_ID}" | cut -d '"' -f2)"

			if [ -n "${BACKUP_USB_UUID}" ]; then
				BACKUP_USB_MOUNT_PATH="/media/${username}/${BACKUP_USB_UUID}"

				if mountpoint -q "${BACKUP_USB_MOUNT_PATH}"; then
					echo "Backup USB is already mounted at ${BACKUP_USB_MOUNT_PATH} at Time: ${datetime}"
				else
					echo "Backup USB mount is not active at ${BACKUP_USB_MOUNT_PATH} at Time: ${datetime}. Attempting to mount it now."

					if sudo mount "${BACKUP_USB_MOUNT_PATH}"; then
						echo "Backup USB mount attempt succeeded at Time: ${datetime}"
					elif udisksctl mount -b "/dev/${BACKUP_USB_BLOCK_ID}"; then
						echo "Backup USB mount attempt succeeded through udisksctl at Time: ${datetime}"
					else
						echo "Backup USB mount attempt failed at Time: ${datetime}. Borg will still be attempted in case the repository is still reachable."
					fi
				fi
			else
				echo "Backup USB UUID was not found at Time: ${datetime}. Borg will still be attempted using the configured repository path."
			fi
		else
			echo "Backup USB block device was not found in lsblk at Time: ${datetime}. Borg will still be attempted using the configured repository path."
		fi
	else
		echo "Backup USB was not found in lsusb at Time: ${datetime}. Attempting Borg anyway in case the repository path is still available."
	fi

	BORG_ENV_FILE="/home/${username}/.flash_borg_env"
	if [ -f "${BORG_ENV_FILE}" ]; then
		source "${BORG_ENV_FILE}"
	else
		echo "Borg environment file ${BORG_ENV_FILE} was not found at Time: ${datetime}. Borg commands may fail until USB backup setup is rerun."
	fi
	read -r -a BACKUP_DIR_ARRAY <<< "${BACKUP_DIRS}"
	SKIP_BORG_CREATE=0

	echo "Starting Borg repository check at Time: ${datetime}"
	if timeout "${BORG_CHECK_TIMEOUT}" borg check --lock-wait 60 --repository-only; then
		echo "Borg repository check passed at Time: ${datetime}"
	else
		echo "Borg repository check failed at Time: ${datetime}. Attempting repair before backup creation."

		if timeout "${BORG_REPAIR_TIMEOUT}" borg check --lock-wait 60 --repair --repository-only; then
			echo "Borg repository repair completed at Time: ${datetime}"
		else
			echo "Borg repository repair failed or timed out at Time: ${datetime}. Skipping Borg backup creation because the repository could not be trusted. Operator escalation is required before the next backup attempt."
			SKIP_BORG_CREATE=1
		fi
	fi

	if [ "${SKIP_BORG_CREATE}" -eq 0 ]; then
		echo "Starting Borg backup creation at Time: ${datetime}"
		if timeout "${BORG_CREATE_TIMEOUT}" borg create --lock-wait 60 --exclude "/home/${username}/data/*.zip" --exclude "/home/${username}/data/*/*face*" "::${participant_id}-FLASH-HA-Data-Backup-${datetime}" "${BACKUP_DIR_ARRAY[@]}"; then
			echo "USB backup without face folders created at Time: ${datetime}"
			echo "Starting Borg prune after successful backup creation at Time: ${datetime}"

			if timeout "${BORG_PRUNE_TIMEOUT}" borg prune --lock-wait 60 --glob-archives "${participant_id}-FLASH-HA-Data-Backup-*" --keep-last 30; then
				echo "Borg prune completed at Time: ${datetime}"
			else
				echo "Borg prune failed or timed out at Time: ${datetime}. The device runtime will continue."
			fi
		else
			echo "Borg backup creation failed or timed out at Time: ${datetime}. The device runtime will continue without stopping FLASH."
		fi
	else
		echo "Borg backup creation was skipped at Time: ${datetime}. The device runtime will continue without stopping FLASH while the operator escalates the untrusted repository state."
	fi

  	source "/home/${username}/py38/bin/activate"
	
	sleep 5;
 
	# Restart the FLASH run on boot service and if on a second loop reboot the device
	if ((loop % 2 == 0)); then
 		reboot
   		systemctl start flash-run-on-boot.service
  	else
		systemctl start flash-run-on-boot.service
  		((loop=loop+1))
 	fi
 	
done
