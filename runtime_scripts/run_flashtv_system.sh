#!/bin/bash

zenity --warning --title "Warning Message" --width 500 --height 100 --text "Please close folder windows or programs (Cheese, incomplete protocols) that you are not using. \n\nReducing the clutter helps."

camStat=`ls /dev/video*`
#echo $camStat
for dev in $camStat
do
	#echo 'cam ident: ' $dev
	camUse=`fuser $dev`
	#echo $camUse
	if [ $camUse ]; then
		#echo 'cam is used', $camUse
		zenity --warning --title "Warning Message" --width 500 --height 100 --text "Camera is being used by another program. \n\nMay be you are running cheese in another terminal somewhere. \nPlease close the other program."
		exit
	fi
done

source data_details.sh
zenity --question --title="Creating the faces" --width 500 --height 100 --text="Please verify the following details\nFamily ID: $famId \nUser Name: $usrName \nData save path: $savePath" --no-wrap
user_resp=$?

if [ $user_resp -eq 1 ]; then
	#echo "Exitted the code $user_resp"
	zenity --warning --text="Exiting the code since data details are not correct. Please modify them and restart the script."
	exit 
	#famId=$(zenity --entry --title="Please input Family ID" --text="Family ID :")
	#usrName=$(zenity --entry --title="Please input Device User Name" --text="User Name :")
	#savePath=$(zenity  --file-selection --title="Choose a directory to save the data" --directory)
	#echo "famId=${famId}" > data_details.sh
	#echo "usrName=${usrName}" >> data_details.sh
	#echo "savePath=${savePath}" >> data_details.sh
fi


#export PYTHONPATH=/home/$USER/mxnet_install/mxnet/python:$PYTHONPATH
source /home/$usrName/.bashrc
echo "PYTHONPATH is" $PYTHONPATH

zenity --question --title="About to run FLASH-TV algorithm" --width 500 --height 100 --text="Click YES to start video streaming" --no-wrap
user_resp=$?

if [ $user_resp -eq 1 ]; then
	echo "Exitted the code $user_resp"
	exit 
fi

source /home/$usrName/py38/bin/activate
#cd /home/$usrName/Desktop/FLASH_TV_v3
cd /home/$usrName/flash-tv-scripts/python_scripts

echo "Everything is a success"

while true;
do
	python test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py $famId $savePath save-image $usrName;
	sleep 30;
done
	



