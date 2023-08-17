#echo $2
#echo $1

famId=$1 
usrName=$2
while true;
do
    sleep 120;
    errlog=/home/$usrName/data/${famId}_data/${famId}_flash_logstderr.log
    if grep -w 'tryIoctl' $errlog; then
        echo "camera warning exists!!" `date`
        systemctl stop flash-run-on-boot.service
        sleep 10
        grep -rl 'tryIoctl' $errlog | xargs sed -i 's/tryIoctl/tryIoctl_addressed/g'
        systemctl start flash-run-on-boot.service
    fi
done
