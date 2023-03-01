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

camStat=`ls /sys/class/video4linux/`
#echo $camStat
for videoId in $camStat
do
	var=`cat /sys/class/video4linux/$videoId/name`
	if (echo "$var" | grep -iq "C930e") ; then # Integrated Camera: Integrated C
		echo "Camera is identified"
		camFound=1
		break
	else 
		camFound=0
	fi
done

if [ $camFound == 0 ]; then
	zenity --warning --title="Warning message" --width 500 --height 100 --text="Exiting the code since Logitech c930e camera is not detected. Please connect the camera and restart the script."
	exit
else 
	break
fi

echo $var, $videoId

#famId=$(zenity --entry --title="Please input Family ID" --text="Family ID :")
source data_details.sh

zenity --question --title="Capturing the video" --width 500 --height 100 --text="Please verify the following details\nFamily ID: $videoFileName \nData save path: $savePath" --no-wrap
user_resp=$?

if [ $user_resp -eq 1 ]; then
	#echo "Exitted the code $user_resp"
	zenity --warning --title="Warning message" --width 500 --height 100 --text="Exiting the code since data details are not correct. Please modify them and restart the script."
	exit 
fi


mkdir -p $savePath

#famId=$(zenity --entry --title="Please input Family ID" --text="Family ID :")

if [ -f $savePath/$videoFileName ]; then
	#zenity --info --title="Building Gallery for FLASH-TV face verification" --width 500 --height 100 --text="Data save path: $savePath \nHas enough space for data collection" --no-wrap
	#zenity --warning --title "Warning Message" --width 500 --height 100 --text "Looks like the directory you selected to save the data does not exist. Please create it and restart"
	#videoFileName=$(zenity --entry --title="Please input video filename" --text="Looks like the directory you selected already has a video file with the name $videoFileName.mp4. Please enter another Name :")
	zenity --warning --title "Warning Message" --width 500 --height 100 --text "There is a already a video file with the same name. Please modify the name in data_details.sh."
	exit
else 
	tmp=10
fi

if [ -d $savePath ]; then
	#zenity --info --title="Building Gallery for FLASH-TV face verification" --width 500 --height 100 --text="Data save path: $savePath \nHas enough space for data collection" --no-wrap
	tmp=10
else 
	#echo "The data save path does not have sufficient space of 50GB, please create more free space."
	zenity --warning --title "Warning Message" --width 500 --height 100 --text "Looks like the directory you selected to save the data does not exist. Please create it and restart"
	exit
fi


minN=100
minI="G"

freeSpace=$(df -Ph $savePath | tail -1 | awk '{print $4}')

freeN=${freeSpace:0:-1}
freeN=${freeN%.*}
freeI=${freeSpace:(-1)}
#freeI="'$freeI
echo $freeN $freeI $minN $minI 

if [ $freeN -gt $minN ] && [ $freeI == $minI ]; then
	#zenity --info --title="Building Gallery for FLASH-TV face verification" --width 500 --height 100 --text="Data save path: $savePath \nHas enough space for data collection" --no-wrap
	tmp=10
else 
	#echo "The data save path does not have sufficient space of 50GB, please create more free space."
	zenity --warning --title "Warning Message" --width 500 --height 100 --text "Disk space is less than 50GB. Create more space in the hard disk."
	exit
fi

zenity --question --title="Video capture for FLASH_TV labeling" --width 500 --height 100 --text="Click YES to start video streaming\n\nThe following details are entered \nVideo Filename: $videoFileName \nData save path: $savePath" --no-wrap
user_resp=$?

if [ $user_resp -eq 1 ]; then
	echo "Exitted the code $user_resp"
	exit 
fi

date > $savePath/"${videoFileName}_time_video_started.txt"
ffmpeg -loglevel error -y -s 1920x1080 -r 30 -f video4linux2 -input_format mjpeg -i /dev/$videoId -c:v copy $savePath/$videoFileName
echo $?
