#!/bin/bash

if [ $# -lt 3 ]; then
    echo "Usage: $0 <participant_id> <username> <data_folder_path>"
    echo "Example: $0 123 flashsys001 /home/flashsys001/data/123001_data"
    exit 1
fi

participant_id="$1"
username="$2"
DATA_FOLDER_PATH="$3"

echo "Creating faces folder with:"
echo "  Participant ID: ${participant_id}"
echo "  Username: ${username}"
echo "  Data Path: ${DATA_FOLDER_PATH}"

zenity --question --title="Verifying Data Details" --width 500 --height 100 --text="Please verify the following data details\nParticipant ID: ${participant_id}\nUsername: ${username}\nData Folder Path: ${DATA_FOLDER_PATH}" --no-wrap
user_resp=$?

if [ ${user_resp} -eq 1 ]; then
	zenity --warning --text="Exiting the code since the data details were not correct according to the user. Please modify them and restart the script."
	exit
fi

FACES_FOLDER_PATH="${DATA_FOLDER_PATH}/${participant_id}_faces"
mkdir -p "${FACES_FOLDER_PATH}"

FACE_CROPS_FOLDER_PATH="${DATA_FOLDER_PATH}/${participant_id}_face_crops"
if [ ! -d "${FACE_CROPS_FOLDER_PATH}" ]; then
    zenity --warning --title "Warning Message" --width 700 --height 100 --text "The indicated face_crops directory ${FACE_CROPS_FOLDER_PATH} does not exist. \nPlease check if the face_crops directory is present."
    exit
fi

min_faces=5

copy_faces() {
    local face_crop_type=$1
    local FACE_CROP_TYPE_SELECTED_PATH="${FACE_CROPS_FOLDER_PATH}/${face_crop_type}_selected"
    local face_crop_type_count=$(find "${FACE_CROP_TYPE_SELECTED_PATH}" -name "*.png" | wc -l)

    # shellcheck disable=SC2086
    if [ ${face_crop_type_count} -lt ${min_faces} ]; then
        zenity --warning --title "Warning Message" --width 700 --height 100 --text "The number of ${face_crop_type} faces selected for the gallery is less than ${min_faces}. \nPlease check if the folder ${FACE_CROP_TYPE_SELECTED_PATH} has less than ${min_faces} faces."
        exit
    fi

    local n=0
    for i in "${FACE_CROP_TYPE_SELECTED_PATH}"/*.png; do
        n=$((n+1))
        cp "${i}" "${FACES_FOLDER_PATH}/${participant_id}_${face_crop_type}${n}.png"
    done
}

copy_faces "tc"
copy_faces "sib"
copy_faces "parent"

extra_images=$(find "${FACE_CROPS_FOLDER_PATH}/extra_selected/" -name "*.png" | wc -l)
# shellcheck disable=SC2086
if [ ${extra_images} -gt 0 ]; then
    copy_faces "extra"
else
    # Copy poster faces if extra faces were not selected
    n=0
    for i in "${HOME}/flash-tv-scripts/poster_faces"/*.png; do
        n=$((n+1))
        cp "${i}" "${FACES_FOLDER_PATH}/${participant_id}_extra${n}.png"
    done

    n_extra_faces=$(find "${FACES_FOLDER_PATH}" -name "${participant_id}_extra*.png" | wc -l)
    if [ ${n_extra_faces} -lt ${min_faces} ]; then
        zenity --warning --title "Warning Message" --width 700 --height 100 --text "The number of extra faces selected for the gallery is less than ${min_faces}. \nPlease check if the folder ${DATA_FOLDER_PATH}/${participant_id}_face_crops/extra_selected has less than ${min_faces} faces."
        exit
    fi
fi

