#!/bin/bash

export famId=123XXX
export usrName=flashsysXXX

export LD_LIBRARY_PATH=/home/$usrName/mxnet/lib:$LD_LIBRARY_PATH
export PATH=/usr/local/cuda-11/bin:$PATH
export MXNET_HOME=/home/$usrName/mxnet
export PYTHONPATH=$MXNET_HOME/python:$PYTHONPATH

while true;
do
	sleep 3600;
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

	sleep 20;
  shutdown -r
done
