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
	zenity --warning --title "Warning Message" --width 700 --height 100 --text "The indicated face_crops directory $savePath/${famId}_face_crops does not exist. \nPlease check if the face_crops directory is present.";
	exit 
fi

# target child processing
ntc=`ls $savePath/"${famId}_face_crops"/tc_selected/*.png | wc -l`
min=5
if [ $ntc -lt $min ]; then
	zenity --warning --title "Warning Message" --width 700 --height 100 --text "The number of target child faces selected for the gallery is less than $min. \nPlease check if the folder $savePath/${famId}_face_crops/tc_selected has less than $min faces."
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
	zenity --warning --title "Warning Message" --width 700 --height 100 --text "The number of sibling faces selected for the gallery is less than $min. \nPlease check if the folder $savePath/${famId}_face_crops/sib_selected has less than $min faces."
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
	zenity --warning --title "Warning Message" --width 700 --height 100 --text "The number of parent faces selected for the gallery is less than $min. \nPlease check if the folder $savePath/${famId}_face_crops/par_selected has less than $min faces."
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


npar=`ls $savePath/"${famId}_face_crops"/extra_selected/*.png | wc -l`
min=5
if [ $npar -lt $min ]; then
	zenity --warning --title "Warning Message" --width 700 --height 100 --text "The extra faces selected for gallery is less than $min. \nPlease check if the folder $savePath/${famId}_face_crops/extra_selected has less than $min faces."
	exit
fi

# extra processing
n=0
extra_images=($savePath/"${famId}_face_crops"/extra_selected/*.png)

if [ -e "${extra_images[0]}" ]; then
    for i in "${extra_images[@]}"; do
        n=$((n+1))
        cp "$i" "$savePath/${famId}_faces/${famId}_extra${n}.png"
    done
else
    # poster processing
    n=0
    for i in ../poster_faces/*.png; do
        n=$((n+1))
        cp "$i" "$savePath/${famId}_faces/${famId}_extra${n}.png"
    done
fi
