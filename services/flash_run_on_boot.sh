#!/bin/bash

export famId=123XXX
export usrName=flashsysXXX

export LD_LIBRARY_PATH=/home/$usrName/mxnet/lib:$LD_LIBRARY_PATH
export PATH=/usr/local/cuda-11/bin:$PATH
export MXNET_HOME=/home/$usrName/mxnet
export PYTHONPATH=$MXNET_HOME/python:$PYTHONPATH


# run time-synchronization commands 
hwclock -s

source /home/$usrName/py38/bin/activate

# runs a while loop for the flash-tv algorithm 
while true;
do
	python /home/$usrName/flash-tv-scripts/python_scripts/test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py $famId /home/$usrName/data/${famId}_data no-save-image $usrName;
	sleep 30;
done



