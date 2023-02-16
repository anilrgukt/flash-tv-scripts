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
	
	mkdir -p "${logFile}/varlogs_${dt}"
	cp /var/log/logstdout.log /var/log/logstderr.log /var/log/logstdoutp.log /var/log/logstderrp.log "${logFile}/varlogs_${dt}"
	
	sleep 20;
	systemctl start flash-run-on-boot.service
done
