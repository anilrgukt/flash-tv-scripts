#!/bin/bash

export famId=123XXX
export usrName=flashsysXXX
export BACKUP_DIRS="/home/${usrName}/data /home/${usrName}/.homeassistant"

logFolder=/home/${usrName}/data/${famId}_data/logs
mkdir -p ${logFolder}

tegrastats --interval 30000 --logfile /home/${usrName}/data/${famId}_data/${famId}_tegrastats.log &
bash /home/${usrName}/flash-tv-scripts/services/flash_check_camera_warnings.sh ${famId} ${usrName} &

i=1
while true;
do
	sleep 60;
	#DOW=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	#dt=`date`;
	dt=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	systemctl status flash-run-on-boot.service > "${logFolder}/log_${dt}.txt"
	systemctl stop flash-run-on-boot.service
	systemctl status flash-run-on-boot.service > "${logFolder}/logend_${dt}.txt"
	timedatectl status > "${logFolder}/timedate_${dt}.txt"
	v4l2-ctl --list-devices > "${logFolder}/camera_${dt}.txt"
	
	pkill -9 -f test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py
	
	mkdir -p "${logFolder}/varlogs_${dt}"
	mv /home/${usrName}/data/${famId}_data/${famId}_flash_logstdout.log /home/${usrName}/data/${famId}_data/${famId}_flash_logstderr.log "${logFolder}/varlogs_${dt}"
	cp /home/${usrName}/data/${famId}_data/${famId}_flash_logstdoutp.log /home/${usrName}/data/${famId}_data/${famId}_flash_logstderrp.log "${logFolder}/varlogs_${dt}"
	#mv /var/log/"${famId}_flash_logstdout.log" /var/log/"${famId}_flash_logstderr.log" "${logFolder}/varlogs_${dt}"
	#cp /var/log/"${famId}_flash_logstdoutp.log" /var/log/"${famId}_flash_logstderrp.log" "${logFolder}/varlogs_${dt}"
	
	sleep 10;
	
	if lsusb | grep -q "SanDisk Corp. Ultra Fit"
	then

		backup_usb_found=1
		
		backup_usb_path=`lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'`

		export BORG_REPO=${backup_usb_path}/USB_Backup_Data_flashsysXXX
		
		export BORG_PASSPHRASE=$(head -n 1 /home/${usrName}/flash-tv-scripts/setup_scripts/borg-passphrase-${usrName}.txt)
		
		# Check if TECH participant (longer family ID) and ignore face folders in backup
		if [ ${#famId} -gt 6 ]; then

			borg create --exclude "/home/$usrName/data/*.zip" --exclude "/home/$usrName/data/*/*face*" ::${famId}-FLASH-HA-Data-Backup-${dt} ${BACKUP_DIRS}
			
			echo "USB Backup without Face Folders Created at Time: ${dt}"
			
		else
		
			borg create --exclude "/home/$usrName/data/*.zip" ::${famId}-FLASH-HA-Data-Backup-${dt} ${BACKUP_DIRS}
						
			echo "USB Backup Created at Time: ${dt}"
			
		fi
		
	else

		backup_usb_found=0

		echo "*****BACKUP USB NOT FOUND*****"
		
	fi

	sleep 10;

	if (($i%2==0))
	then
		#reboot
		echo "reboot"
  	else
		systemctl start flash-run-on-boot.service
  		((i=i+1))
 	fi
 	
done
