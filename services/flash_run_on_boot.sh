#!/bin/bash

export participant_id=123XXX
export username=flashsysXXX
export DATA_FOLDER_PATH="/home/${username}/data/${participant_id}_data"

export LD_LIBRARY_PATH="/home/${username}/mxnet/lib:${LD_LIBRARY_PATH}"
export PATH="/usr/local/cuda-11/bin:${PATH}"
export MXNET_HOME="/home/${username}/mxnet"
export PYTHON_PATH="${MXNET_HOME}/python:${PYTHON_PATH}"

# Activate Python 3.8 virtual environment with libraries set up
source "/home/${username}/py38/bin/activate"

# Disable automatic time updating and update the time from the RTCs instead
timedatectl set-ntp 0;
sleep 1;
python3 "/home/${username}/flash-tv-scripts/python_scripts/update_or_check_system_time_from_RTCs.py" "update" "/home/${username}/data/${participant_id}_data/${participant_id}_start_date.txt"

# Create a local network (without internet) to connect to when transferring data at visit 2
device_suffix="${username: -3}"

if [[ ! "${device_suffix}" =~ ^[0-9]{3}$ ]]; then
    echo "Error: Username '${username}' does not end with a valid 3-digit FLASH-TV device suffix."
    exit 1
fi

suffix=$((10#${device_suffix}))

if [ "${suffix}" -lt 1 ] || [ "${suffix}" -gt 255 ]; then
    echo "Error: FLASH-TV device suffix '${device_suffix}' is not a valid host address for 10.0.0.x."
    exit 1
fi

ip_assign_output=$(sudo ip addr add 10.0.0."${suffix}"/24 dev eth0 2>&1)
ip_assign_status=$?

if [ "${ip_assign_status}" -eq 0 ]; then
    echo "Info: Assigned IP 10.0.0.${suffix}/24 to eth0 successfully."
elif [[ "${ip_assign_output}" == *"RTNETLINK answers: File exists"* ]]; then
    echo "Info: IP 10.0.0.${suffix}/24 was already assigned to eth0."
else
    echo "Error: Failed to assign IP 10.0.0.${suffix}/24 to eth0."
    echo "Error: ip addr add output: ${ip_assign_output}"
    exit 1
fi

# Run a while loop for the FLASH-TV algorithm only if it doesn't already exist
while true;
do	
if ! [ "$(pgrep -af run_flash_data_collection.py)" ]; then
	free -m && sync && echo 1 > /proc/sys/vm/drop_caches && free -m;

 	sleep 1;

	python /home/${username}/flash-tv-scripts/python_scripts/run_flash_data_collection.py "${participant_id}" "${DATA_FOLDER_PATH}" no-save-image "${username}";
	
	sleep 30;
else
	sleep 30;
fi
done
