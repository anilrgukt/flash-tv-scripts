#!/bin/bash

export famId=123XXX
export usrName=flashsysXXX

export LD_LIBRARY_PATH=/home/$usrName/mxnet/lib:$LD_LIBRARY_PATH
export PATH=/usr/local/cuda-11/bin:$PATH
export MXNET_HOME=/home/$usrName/mxnet
export PYTHONPATH=$MXNET_HOME/python:$PYTHONPATH

index_path="/home/$usrName/data/${famId}_data/${famId}_index.txt"

source /home/$usrName/py38/bin/activate
python /home/${usrName}/flash-tv-scripts/python_scripts/check_file_events.py $famId /home/${usrName}/data/${famId}_data /home/${usrName}/data/${famId}_flashlog_filesequence.csv &

timedatectl set-ntp 0;
sleep 5;
python3 /home/$usrName/flash-tv-scripts/python_scripts/update_system_time_from_RTCs.py

if [ -e "$index_path" ]; then
    last_number=$(tail -n 1 "$index_path")
    new_number=$((last_number + 1))
else
    new_number=1
fi

echo "$new_number" >> "$index_path"

# runs a while loop for the FLASH-TV algorithm only if it doesn't already exist
while true;
do	
if ! [ "`pgrep -af test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py`" ]
then
	free -m && sync && echo 1 > /proc/sys/vm/drop_caches && free -m;
 	sleep 10;
	python /home/$usrName/flash-tv-scripts/python_scripts/test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py $famId /home/$usrName/data/${famId}_data no-save-image $usrName;
 
	sleep 30;
else
	sleep 30;
fi
done



