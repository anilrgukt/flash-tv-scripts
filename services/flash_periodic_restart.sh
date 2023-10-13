#!/bin/bash

export famId=123XXX
export usrName=flashsysXXX
export BACKUP_DIRS="/home/${usrName}/data /home/${usrName}/.homeassistant"

#logFolderPath=/home/$usrName/data/${famId}_data
logFolder=/home/$usrName/data/${famId}_data/logs
mkdir -p $logFolder

reboot_index_path="/home/$usrName/data/${famId}_data/${famId}_reboot_index.txt"

tegrastats --interval 30000 --logfile /home/${usrName}/data/${famId}_data/${famId}_tegrastats.log &
bash /home/${usrName}/flash-tv-scripts/services/flash_check_camera_warnings.sh ${famId} ${usrName} &

source /home/$usrName/py38/bin/activate
python /home/${usrName}/flash-tv-scripts/python_scripts/check_file_events.py $famId $logFolder /home/${usrName}/data/${famId}_data/${famId}_varlog_filesequence.csv &

sleep 10;

if [ -e "$reboot_index_path" ]; then
    last_number=$(tail -n 1 "$reboot_index_path")
    new_number=$((last_number + 1))
else
    new_number=1
fi
dt_for_index=$(date +"%d_%b_%Y_%H-%M-%S_%Z")

echo "flash_periodic_restart.sh was just restarted around ${dt_for_index}, implying that the current reboot index is: ${new_number}" >> "$reboot_index_path"

i=1
while true;
do
	sleep 21600;
	#DOW=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	#dt=`date`;
	 
	dt=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	
	mkdir -p "${logFolder}/varlogs_${dt}"
	echo "Reboot Index: ${new_number}" >> "${logFolder}/varlogs_${dt}/log_${dt}.txt"
	systemctl status flash-run-on-boot.service >> "${logFolder}/varlogs_${dt}/log_${dt}.txt"
	systemctl stop flash-run-on-boot.service
	echo "Reboot Index: ${new_number}" >> "${logFolder}/varlogs_${dt}/logend_${dt}.txt"
	systemctl status flash-run-on-boot.service >> "${logFolder}/varlogs_${dt}/logend_${dt}.txt"
	echo "Reboot Index: ${new_number}" >> "${logFolder}/varlogs_${dt}/timedate_${dt}.txt"
	python3 /home/$usrName/flash-tv-scripts/python_scripts/check_all_times.py >> "${logFolder}/varlogs_${dt}/timedate_${dt}.txt"
	v4l2-ctl --list-devices > "${logFolder}/varlogs_${dt}/camera_${dt}.txt"
	
	pkill -9 -f test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py
	
	mv /home/$usrName/data/${famId}_data/${famId}_flash_logstdout.log /home/$usrName/data/${famId}_data/${famId}_flash_logstderr.log "${logFolder}/varlogs_${dt}"
	cp /home/$usrName/data/${famId}_data/${famId}_flash_logstdoutp.log /home/$usrName/data/${famId}_data/${famId}_flash_logstderrp.log "${logFolder}/varlogs_${dt}"
	#mv /var/log/"${famId}_flash_logstdout.log" /var/log/"${famId}_flash_logstderr.log" "${logFolder}/varlogs_${dt}"
	#cp /var/log/"${famId}_flash_logstdoutp.log" /var/log/"${famId}_flash_logstderrp.log" "${logFolder}/varlogs_${dt}"
 
 	if [ ! `lsusb | grep -q "SanDisk Corp. Ultra Fit"` ] && [ `lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'` ]; then
	
		backup_usb_path=`lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'`
	
		export BORG_REPO=${backup_usb_path}/USB_Backup_Data_flashsysXXX
		
		export BORG_PASSPHRASE=$(head -n 1 /home/${usrName}/flash-tv-scripts/setup_scripts/borg-passphrase-${usrName}.txt)
		
		# Check if TECH participant (longer family ID) and ignore face folders in backup
		if [ ${#famId} -gt 6 ]; then
	
			borg create --exclude "/home/${usrName}/data/*.zip" --exclude "/home/${usrName}/data/*/*face*" ::${famId}-FLASH-HA-Data-Backup-${dt} ${BACKUP_DIRS}
			
			echo "USB Backup without Face Folders Created at Time: ${dt}"
			
		else
		
			borg create --exclude "/home/${usrName}/data/*.zip" ::${famId}-FLASH-HA-Data-Backup-${dt} ${BACKUP_DIRS}
						
			echo "USB Backup Created at Time: ${dt}"
			
		fi
			
	else
 
		if [ ! `lsusb | grep -q "SanDisk Corp. Ultra Fit"` ]; then
		
			echo "Backup USB not Found in lsusb at Time: ${dt}"
		fi	
  
		if [ `lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'` ]; then
		
			echo "Backup USB not Found in lsblk at Time: ${dt}"
		fi
  
	fi
	
	sleep 5;
 
	if (($i%2==0)); then
 		reboot
   		systemctl start flash-run-on-boot.service
  	else
		systemctl start flash-run-on-boot.service
  		((i=i+1))
 	fi
 	
done
