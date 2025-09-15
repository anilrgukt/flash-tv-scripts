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
	if lsusb | grep -q "SanDisk Corp. Ultra Fit"; then	

		if [ "$(lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}')" ]; then
	 
	 		BACKUP_USB_PATH="$(lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}')"

		else
		
			echo "Backup USB not Found in lsblk at Time: ${datetime}"
			
	 	fi
	
	else
		
		echo "Backup USB not Found in lsusb at Time: ${datetime}"
  
	fi

 	source "/home/${username}/.bashrc"


	
	borg create --exclude "/home/${username}/data/*.zip" --exclude "/home/${username}/data/*/*face*" "::${participant_id}-FLASH-HA-Data-Backup-${datetime}" ${BACKUP_DIRS}
		
	echo "USB Backup without Face Folders Created at Time: ${datetime}"

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
