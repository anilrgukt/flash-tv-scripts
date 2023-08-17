#echo $2
#echo $1

famId=$1 
userName=$2
while True
do
	sleep 120;
	if grep -w 'tryIoctl' /home/$usrName/data/${famId}_data/${famId}_flash_logstderr.log; then
	    systemctl stop flash-run-on-boot.service
	    sleep 10
	    systemctl start flash-run-on-boot.service
	fi
done
