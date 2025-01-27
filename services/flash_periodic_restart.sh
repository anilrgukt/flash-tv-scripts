#!/bin/bash

export participantID=123XXX
export username=flashsysXXX
export logFolder="/home/${username}/data/${participantID}_data/logs"

source "/home/${username}/py38/bin/activate"

#logFolderPath=/home/$username/data/${participantID}_data
mkdir -p ${logFolder}

python3 "/home/${username}/flash-tv-scripts/python_scripts/check_file_events.py" ${participantID} ${logFolder} "/home/${username}/data/${participantID}_data/${participantID}_varlog_filesequence.csv" &

python3 "/home/${username}/flash-tv-scripts/python_scripts/check_file_events.py" ${participantID} "/home/${username}/data/${participantID}_data /home/${username}/data/${participantID}_data/${participantID}_flashlog_filesequence.csv" &

tegrastats --interval 30000 --logfile "/home/${username}/data/${participantID}_data/${participantID}_tegrastats.log" &

bash "/home/${username}/flash-tv-scripts/services/flash_check_camera_warnings.sh" ${participantID} ${username} &

BEACON_SCANNER_PROGRAM_PATH="/home/${username}/flash-tv-scripts/services/bt_beacon_accelerometer_scanner"

if [ -e "${BEACON_SCANNER_PROGRAM_PATH}" ]; then

    bash "/home/${username}/flash-tv-scripts/services/run_beacon_scanner.sh" ${BEACON_SCANNER_PROGRAM_PATH} &

else

    cc "${BEACON_SCANNER_PROGRAM_PATH}.c" -lbluetooth -o ${BEACON_SCANNER_PROGRAM_PATH}
    
    bash "/home/${username}/flash-tv-scripts/services/run_beacon_scanner.sh" ${BEACON_SCANNER_PROGRAM_PATH} &

fi

sleep 10;

REBOOT_INDEX_PATH="/home/${username}/data/${participantID}_data/${participantID}_reboot_index.txt"

if [ -e ${REBOOT_INDEX_PATH} ]; then

    last_line=$(tail -n 1 ${REBOOT_INDEX_PATH})
    
    last_index=$(echo "${last_line}" | awk '{print $NF}')
    
    new_index=$((last_index + 1))
    
else

    new_index=1
    
fi

dt_for_index=$(date +"%d_%b_%Y_%H-%M-%S_%Z")

echo "flash_periodic_restart.sh was just restarted around ${dt_for_index}, implying that the current reboot index is: ${new_index}" >> "${REBOOT_INDEX_PATH}"

loop=1
while true;
do
	sleep 21600;
	#DOW=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	#dt=`date`;
	 
	dt=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	
	mkdir -p "${logFolder}/varlogs_${dt}"
	echo "Reboot Index: ${new_index}" >> "${logFolder}/varlogs_${dt}/log_${dt}.txt"
	systemctl status flash-run-on-boot.service >> "${logFolder}/varlogs_${dt}/log_${dt}.txt"
	systemctl stop flash-run-on-boot.service
	echo "Reboot Index: ${new_index}" >> "${logFolder}/varlogs_${dt}/logend_${dt}.txt"
	systemctl status flash-run-on-boot.service >> "${logFolder}/varlogs_${dt}/logend_${dt}.txt"
	echo "Reboot Index: ${new_index}" >> "${logFolder}/varlogs_${dt}/timedate_${dt}.txt"
	python3 /home/${username}/flash-tv-scripts/python_scripts/check_all_times.py >> "${logFolder}/varlogs_${dt}/timedate_${dt}.txt"
	v4l2-ctl --list-devices > "${logFolder}/varlogs_${dt}/camera_${dt}.txt"
	
	pkill -9 -f run_flash_data_collection.py
	
	mv "/home/${username}/data/${participantID}_data/${participantID}_flash_logstdout.log" "/home/${username}/data/${participantID}_data/${participantID}_flash_logstderr.log" "${logFolder}/varlogs_${dt}"
	cp "/home/${username}/data/${participantID}_data/${participantID}_flash_logstdoutp.log" "/home/${username}/data/${participantID}_data/${participantID}_flash_logstderrp.log" "${logFolder}/varlogs_${dt}"
	#mv /var/log/"${participantID}_flash_logstdout.log" /var/log/"${participantID}_flash_logstderr.log" "${logFolder}/varlogs_${dt}"
	#cp /var/log/"${participantID}_flash_logstdoutp.log" /var/log/"${participantID}_flash_logstderrp.log" "${logFolder}/varlogs_${dt}"
 
	if ! lsusb | grep -q "SanDisk Corp. Ultra Fit"; then	

		if [ "$(lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}')" ]; then
	 
	 		BACKUP_USB_PATH="$(lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}')"

		else
		
			echo "Backup USB not Found in lsblk at Time: ${dt}"
			
	 	fi

 		source "/home/${username}/.bashrc"

  		export BACKUP_DIRS="/home/${username}/data /home/${username}/docker-compose/ha-config"
	
		borg create --exclude "/home/${username}/data/*.zip" --exclude "/home/${username}/data/*/*face*" "::${participantID}-FLASH-HA-Data-Backup-${dt}" "${BACKUP_DIRS}"
		
		echo "USB Backup without Face Folders Created at Time: ${dt}"

  		source "/home/${username}/py38/bin/activate"
			
	else
		
		echo "Backup USB not Found in lsusb at Time: ${dt}"
  
	fi
	
	sleep 5;
 
	if ((loop % 2 == 0)); then
 		reboot
   		systemctl start flash-run-on-boot.service
  	else
		systemctl start flash-run-on-boot.service
  		((loop=loop+1))
 	fi
 	
done
