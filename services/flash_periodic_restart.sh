#!/bin/bash

export famId=123XXX
export usrName=flashsysXXX

#logFolderPath=/home/$usrName/data/${famId}_data
logFolder=/home/$usrName/data/${famId}_data/logs
mkdir -p $logFolder

tegrastats --interval 30000 --logfile /home/$usrName/data/${famId}_data/${famId}_tegrastats.log &
bash /home/$usrName/flash-tv-scripts/services/flash_check_camera_warnings.sh $famId $usrName &

source /home/$usrName/py38/bin/activate

timedatectl set-ntp 0;
sleep 5;
python3 /home/$usrName/flash-tv-scripts/python_scripts/update_system_time_from_RTCs.py

i=1
while true;
do
	sleep 21600;
	#DOW=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
	#dt=`date`;
	dt=$(date +"%d_%b_%Y_%H-%M-%S_%Z")
 	mkdir -p "${logFolder}/varlogs_${dt}"
	systemctl status flash-run-on-boot.service > "${logFolder}/varlogs_${dt}/log_${dt}.txt"
	systemctl stop flash-run-on-boot.service
	systemctl status flash-run-on-boot.service > "${logFolder}/varlogs_${dt}/logend_${dt}.txt"
	python3 /home/$usrName/flash-tv-scripts/python_scripts/check_all_times.py > "${logFolder}/varlogs_${dt}/timedate_${dt}.txt"
	v4l2-ctl --list-devices > "${logFolder}/varlogs_${dt}/camera_${dt}.txt"
	
	pkill -9 -f test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py
	
	
	mv /home/$usrName/data/${famId}_data/${famId}_flash_logstdout.log /home/$usrName/data/${famId}_data/${famId}_flash_logstderr.log "${logFolder}/varlogs_${dt}"
	cp /home/$usrName/data/${famId}_data/${famId}_flash_logstdoutp.log /home/$usrName/data/${famId}_data/${famId}_flash_logstderrp.log "${logFolder}/varlogs_${dt}"
	#mv /var/log/"${famId}_flash_logstdout.log" /var/log/"${famId}_flash_logstderr.log" "${logFolder}/varlogs_${dt}"
	#cp /var/log/"${famId}_flash_logstdoutp.log" /var/log/"${famId}_flash_logstderrp.log" "${logFolder}/varlogs_${dt}"
	
	sleep 5;
 
	if (($i%2==0))
	then
 		reboot
  	else
		systemctl start flash-run-on-boot.service
  		((i=i+1))
 	fi
done
