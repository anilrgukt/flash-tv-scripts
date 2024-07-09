#!/bin/bash

export famId=123XXX
export usrName=flashsysXXX

export LD_LIBRARY_PATH=/home/$usrName/mxnet/lib:$LD_LIBRARY_PATH
export PATH=/usr/local/cuda-11/bin:$PATH
export MXNET_HOME=/home/$usrName/mxnet
export PYTHONPATH=$MXNET_HOME/python:$PYTHONPATH

source /home/${usrName}/py38/bin/activate
python /home/${usrName}/flash-tv-scripts/python_scripts/check_file_events.py $famId /home/${usrName}/data/${famId}_data /home/${usrName}/data/${famId}_data/${famId}_flashlog_filesequence.csv &

timedatectl set-ntp 0;
sleep 1;
python3 /home/${usrName}/flash-tv-scripts/python_scripts/update_system_time_from_RTCs.py /home/${usrName}/data/${famId}_data/${famId}_start_date.txt

suffix="${usrName: -2}"

if [ ! $(sudo ip addr add 10.0.0.${suffix}/24 dev eth0 | grep "RTNETLINK answers: File exists") ]; then
	echo "Info: IP was possibly already assigned in this reboot cycle as the 'RTNETLINK answers: File exists' message was detected.";​	
fi

# runs a while loop for the FLASH-TV algorithm only if it doesn't already exist

while true;
do	
if ! [ "`pgrep -af run_flash_data_collection.py`" ]; then
	free -m && sync && echo 1 > /proc/sys/vm/drop_caches && free -m;

 	sleep 1;
	python /home/$usrName/flash-tv-scripts/python_scripts/run_flash_data_collection.py $famId /home/$usrName/data/${famId}_data no-save-image $usrName;
	sleep 30;
else
	sleep 30;
fi
done


