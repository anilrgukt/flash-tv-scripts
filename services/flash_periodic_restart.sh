#!/bin/bash

export famId=123XXX
export usrName=flashsysXXX

#logFilePath=/home/$usrName/data/${famId}_data
logFile=/home/$usrName/data/${famId}_data/logs
mkdir -p $logFile

export BORG_PASSPHRASE=$(head -n 1 /home/$usrName/flash-tv-scripts/setup_scripts/borg-passphrase-${usrName}.txt)

if lsusb | grep "SanDisk Corp. Ultra Fit"

then

	usb_path=`lsblk -o NAME,TRAN,MOUNTPOINT | grep -A 1 -w usb | grep -v usb | awk '{print $2}'`

	export BORG_REPO=$usb_path/USB_Backup_Data_flashsysXXX
	
	usb_found=1

else

	echo "*****BACKUP USB NOT FOUND*****"
	usb_found=0

fi

tegrastats --interval 30000 --logfile /home/$usrName/data/${famId}_data/${famId}_tegrastats.log &
bash /home/$usrName/flash-tv-scripts/services/flash_check_camera_warnings.sh $famId $usrName &

i=1
while true;
do
	sleep 21600;
	#DOW=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	#dt=`date`;
	dt=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	systemctl status flash-run-on-boot.service > "${logFile}/log_${dt}.txt"
	systemctl stop flash-run-on-boot.service
	systemctl status flash-run-on-boot.service > "${logFile}/logend_${dt}.txt"
	timedatectl status > "${logFile}/timedate_${dt}.txt"
	v4l2-ctl --list-devices > "${logFile}/camera_${dt}.txt"
	
	pkill -9 -f test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py
	
	mkdir -p "${logFile}/varlogs_${dt}"
	mv /home/$usrName/data/${famId}_data/${famId}_flash_logstdout.log /home/$usrName/data/${famId}_data/${famId}_flash_logstderr.log "${logFile}/varlogs_${dt}"
	cp /home/$usrName/data/${famId}_data/${famId}_flash_logstdoutp.log /home/$usrName/data/${famId}_data/${famId}_flash_logstderrp.log "${logFile}/varlogs_${dt}"
	#mv /var/log/"${famId}_flash_logstdout.log" /var/log/"${famId}_flash_logstderr.log" "${logFile}/varlogs_${dt}"
	#cp /var/log/"${famId}_flash_logstdoutp.log" /var/log/"${famId}_flash_logstderrp.log" "${logFile}/varlogs_${dt}"
	
	sleep 10;
	
	if [ $usb_found -eq 1 ]
	then
	
		# Check if TECH participant (longer family ID) and ignore face folders in backup
		if [ ${#famId} -ge 6]; then
		
			borg create ::${usrName}-${famId}-FLASH-HA-Data-Backup-{now} \
			/home/$usrName/data                                          \	
			/home/$usrName/.homeassistant                                \
			--exclude '/home/$usrName/data/*face*'
			
			echo "Backup without face folders created at time $dt"
		else
		
			borg create ::${usrName}-${famId}-FLASH-HA-Data-Backup-{now} \
			/home/$usrName/data                                          \	
			/home/$usrName/.homeassistant                                
			
			echo "Backup created at time $dt"
		fi
		
		sleep 10;
		
	fi
 
	if (($i%2==0))
	then
 		reboot
  	else
		systemctl start flash-run-on-boot.service
  		((i=i+1))
 	fi
done
