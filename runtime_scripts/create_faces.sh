#!/bin/bash
source data_details.sh

zenity --question --title="Creating the faces" --width 500 --height 100 --text="Please verify the following details\nFamily ID: $famId \nData save path: $savePath" --no-wrap
user_resp=$?

if [ $user_resp -eq 1 ]; then
	#echo "Exitted the code $user_resp"
	zenity --warning --text="Exiting the code since data details are not correct. Please modify them and restart the script."
	exit 
fi

mkdir -p $savePath/"${famId}_faces"


if [ ! -d $savePath/"${famId}_face_crops" ]
then
	zenity --warning --title "Warning Message" --width 700 --height 100 --text "The face crops directory indicated $savePath/${famId}_face_crops does not exist. \nPlease check data save path if the face crops directory is present. \nPlease restart with right data save path ";
	exit 
fi

# target child processing
ntc=`ls $savePath/"${famId}_face_crops"/tc_selected/*.png | wc -l`
min=5
if [ $ntc -lt $min ]; then
	zenity --warning --title "Warning Message" --width 700 --height 100 --text "The Target child faces selected for gallery are less than $min. \nPlease check folder $savePath/${famId}_face_crops/tc_selected if it has 5 faces. \nPlease restart with right data save path "
	exit
fi


n=0
for i in $savePath/"${famId}_face_crops"/tc_selected/*.png;
do 
	#echo $i;
	n=$((n+1))
	cp $i $savePath/"${famId}_faces"/"${famId}_tc${n}.png"
done

nsib=`ls $savePath/"${famId}_face_crops"/sib_selected/*.png | wc -l`
min=5
if [ $nsib -lt $min ]; then
	zenity --warning --title "Warning Message" --width 700 --height 100 --text "The Sibling faces selected for gallery are less than $min. \nPlease check folder $savePath/${famId}_face_crops/sib_selected if it has 5 faces. \nPlease restart with right data save path "
	exit
fi


# sibling processing
n=0
for i in $savePath/"${famId}_face_crops"/sib_selected/*.png;
do 
	#echo $i;
	n=$((n+1))
	cp $i $savePath/"${famId}_faces"/"${famId}_sib${n}.png"
done


npar=`ls $savePath/"${famId}_face_crops"/par_selected/*.png | wc -l`
min=5
if [ $npar -lt $min ]; then
	zenity --warning --title "Warning Message" --width 700 --height 100 --text "The Parent faces selected for gallery are less than $min. \nPlease check folder $savePath/${famId}_face_crops/par_selected if it has 5 faces. \nPlease restart with right data save path "
	exit
fi

# parent processing
n=0
for i in $savePath/"${famId}_face_crops"/par_selected/*.png;
do 
	#echo $i;
	n=$((n+1))
	cp $i $savePath/"${famId}_faces"/"${famId}_parent${n}.png"
done

# poster processing
n=0
for i in ../poster_faces/*.png;
do 
	#echo $i;
	n=$((n+1))
	cp $i $savePath/"${famId}_faces"/"${famId}_poster${n}.png"
done
