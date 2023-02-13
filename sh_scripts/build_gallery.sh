#!/bin/bash
pkill -9 -f cv2_capture_automate.py
#source /home/flash/Desktop/data_details.sh


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


famId=$(zenity --entry --width 500 --height 100 --title="Please input Family ID" --text="Family ID :")
savePath=$(zenity --width 700 --height 500  --file-selection --title="Choose a directory to save the data" --directory)

echo "famId=${famId}" > data_details.sh
echo "savePath=${savePath}" >> data_details.sh
#famId=$(zenity --entry --title="Please input Family ID" --text="Family ID :")


zenity --question --title="Building Gallery for FLASH-TV face verification" --width 500 --height 100 --text="Please verify the following details\nFamily ID: $famId \nData save path: $savePath" --no-wrap
user_resp=$?

if [ $user_resp -eq 1 ]; then
	echo "Exitted the code $user_resp"
	exit 
fi

zenity --question --title="Building Gallery for FLASH-TV face verification" --width 500 --height 100 --text="Click YES to start video streaming\nFamily ID: $famId \nData save path: $savePath" --no-wrap
user_resp=$?

if [ $user_resp -eq 1 ]; then
	echo "Exitted the code $user_resp"
	exit 
fi

source /home/$USER/py38/bin/activate
cd /home/$USER/Desktop/FLASH_TV_v3

echo "Everything is a success"

python cv2_capture_automate.py $famId $savePath



