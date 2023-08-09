# Family Level Assessment of Screen Use in the Home-Television (FLASH-TV) Scripts
> FLASH-TV installation, setup, configuration, and runtime scripts
<img src="pngs/teaser_small.png"/>

Please refer to these publications for technical details:
 - Vadathya et al. An Objective System for Quantitative Assessment of Television Viewing Among Children (Family Level Assessment of Screen Use in the Home-Television): System Development Study, _JMIR Pediatrics and Parenting 5.1 (2022): e33569._

## Installation Instructions 
Please download the files from this Google Drive [link](https://drive.google.com/drive/folders/1hth1P58s5V-CGqdMYpZw2_dalI-RecTm?usp=share_link) and follow the below instructions
> Prerequisites: Nvidia CUDA enabled GPU (8GB memory), Python3, PyTorch, MXNet

 - Place the extracted .zip files from the download into the locations as specified in `setup_scripts/file_setup.sh`
 - Run `install_scripts/flash_install.sh` to install all the components necessary for FLASH-TV (insightface, darknet face release)
 - This creates a Python virtual environment at `/home/$usrName/py38` from which we execute FLASH-TV algorithms

## FLASH-TV Demo 
 - After the above installation steps are executed without any errors:
 - Create a sample gallery of faces that you want to recognize. Take a look at the example gallery in `examples/gallery_faces`
 - Please read the below instructions completely before executing FLASH-TV
 - Run FLASH-TV v3.0 as indicated in `runtime_scripts/run_flashtv_system.sh`
  
  > Sample execution code
  For example, create a folder for saving data at `/home/user/123_data`. Create a sample gallery similar to the [example](examples/gallery_faces) and name it as `123_faces` and put in the `123_data` folder.
  
  ```
  source /home/$usrName/py38/bin/activate
  cd /home/$usrName/flash-tv-scripts/python_scripts
  python test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py $famId $savePath save-image $usrName
  ```
  
  - `famId` is a 3 digit unique ID for the specific data e.g. 123
  - `savePath` specifies the location where data is saved e.g. `/home/user/123_data`
  - `save-image` indicates whether to save image outputs, to not save specify `no-save-image`
  - `usrName` indicates the user name of the user account

# Details for data collection - FLASH-TV Installation on NVIDIA Jetson AGX Orin Devkits
Please read the [setup instructions](./Device_Setup_Instructions%2008-09-2023.pdf) and [Home Assistant usage](./Home_Assistant_Usage%2008-09-2023.pdf) files above for details
> Make sure you have downloaded or copied the necessary software (insight_face, darknet_face_release etc.) and placed it in the right locations(\*placement only, when specific external hard disk is connected)

 - full_initial_configuration.sh
   > Bash script that automatically runs or sets up other bash scripts for procedures marked with an asterisk(\*), needs to be run once on every new Jetson

 - install_scripts
   > Bash scripts for installing ML libaries and packages necessary for running FLASH-TV and Home Assistant on the Jetsons\*

# FLASH-TV In-Home Data Collection
Please see the [procedure](https://docs.google.com/document/d/1YsyBKnJgQ7WB-XFTUHe-cB27ZMZT5CRpLUyl3zfOLHs/) and [slides](https://bcmedu-my.sharepoint.com/:f:/g/personal/207282_bcm_edu/EqhtrTeGWm9DqhoshCBtBtUB0J5otZWmKRoay09M_0a9Hw?e=gyoOaa) for detailed instructions. The procedure is also hosted as a [pdf](./FLASH-TV_In-Home_Installation_Checklist%2008-09-2023.pdf) in this repository and updated periodically.
  > Bash scripts for running initial FLASH-TV protocols for setup, including building the gallery, creating faces, and running TV gaze estimation with images saved
- setup_scripts
  > Bash scripts for the initial setup of the Jetsons in order to be able to run the other scripts and services and properly save data\*
- services
  > Services for systemd and bash scripts that will run FLASH-TV and Home Assistant on boot and restart FLASH-TV periodically(\*setup only)
 
  > Enable, start, and check the status of all relevant services quickly with test_services.sh if necessary
  
  > Disable and stop all relevant services quickly with stop_services.sh if necessary
- participant_change.sh 
  > Bash script that automatically runs other bash scripts for changing the setup (IDs, services) when changing participants
- video_capture_scripts
  > Bash scripts used on a laptop for video data collection for human ground truth labeling, deleted on Jetsons(\*deletion only)
- python_scripts
  > Python scripts for running FLASH-TV detection, recognition, and target child's gaze estimation
