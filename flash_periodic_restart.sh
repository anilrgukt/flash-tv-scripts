#!/bin/bash

export famId=XXX
export usrName=flashsysXXX

logFilePath=/home/$usrName/data/${famId}_data
logFile=/home/$usrName/data/${famId}_data/logs
mkdir -p $logFile

while true;
do
	sleep 600;
	export dt=`date`;
	systemctl status flash-run-on-boot.service > "${logFile}/log_${dt}.txt"
	systemctl stop flash-run-on-boot.service
	systemctl status flash-run-on-boot.service > "${logFile}/logend_${dt}.txt"
	
	pkill -9 -f test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py
	
	mkdir -p "${logFile}/varlogs_${dt}"
	mv /var/log/"${famId}_flash_logstdout.log" /var/log/"${famId}_flash_logstderr.log" "${logFile}/varlogs_${dt}"
	cp /var/log/"${famId}_flash_logstdoutp.log" /var/log/"${famId}_flash_logstderrp.log" "${logFile}/varlogs_${dt}"
	
	sleep 20;
	systemctl start flash-run-on-boot.service
done
