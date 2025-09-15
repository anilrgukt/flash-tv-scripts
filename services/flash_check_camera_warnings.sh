#!/bin/bash
#echo $2
#echo $1

participantID=$1 
username=$2
while true;
do
    sleep 120;
    errlog="/home/${username}/data/${participantID}_data/${participantID}_flash_logstderr.log"
    if [ -f "$errlog" ]; then
        if grep -w 'tryIoctl' "${errlog}"; then
            echo "camera warning exists!!" "$(date)"
            systemctl stop flash-run-on-boot.service
            sleep 10
            grep -rl 'tryIoctl' "${errlog}" | xargs sed -i 's/tryIoctl/tryIoctl_addressed/g'
            systemctl start flash-run-on-boot.service
        fi
    fi
done
