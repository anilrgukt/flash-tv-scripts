#!/bin/bash

export participantID=123XXX
export username=flashsysXXX

export LD_LIBRARY_PATH=/home/$username/mxnet/lib:$LD_LIBRARY_PATH
export PATH=/usr/local/cuda-11/bin:$PATH
export MXNET_HOME=/home/$username/mxnet
export PYTHONPATH=$MXNET_HOME/python:$PYTHONPATH

source /home/${username}/py38/bin/activate

timedatectl set-ntp 0;
sleep 1;
python3 /home/${username}/flash-tv-scripts/python_scripts/update_system_time_from_RTCs.py /home/${username}/data/${participantID}_data/${participantID}_start_date.txt

suffix=$(printf "%d" "${username: -2}")

if ! sudo ip addr add 10.0.0."${suffix}"/24 dev eth0 2>&1 | grep -q 'RTNETLINK answers: File exists'; then
    echo "Info: IP was possibly already assigned in this reboot cycle as the 'RTNETLINK answers: File exists' message was detected."
fi

# runs a while loop for the FLASH-TV algorithm only if it doesn't already exist

while true;
do	
if ! [ "$(pgrep -af run_flash_data_collection.py)" ]; then
	free -m && sync && echo 1 > /proc/sys/vm/drop_caches && free -m;

 	sleep 1;
	python /home/${username}/flash-tv-scripts/python_scripts/run_flash_data_collection.py ${participantID} /home/${username}/data/${participantID}_data no-save-image ${username};
	sleep 30;
else
	sleep 30;
fi
done


