# FLASH-TV Scripts

> FLASH-TV installation, setup, configuration, and runtime scripts

<img src="pngs/teaser_small.png"/>

# FLASH-TV Installation on NVIDIA Jetson AGX Orin Devkits
Please read the [setup instructions](./Setup_Instructions.pdf) file above for details
> Make sure you have downloaded or copied the necessary software (insight_face, darknet_face_release etc.) and placed it in the right locations(\*placement only, when specific external hard disk is connected)

 - full_initial_configuration.sh
   > Bash script that automatically runs or sets up other bash scripts for procedures marked with an asterisk(\*), needs to be run once on every new Jetson

 - install_scripts
   > Bash scripts for installing ML libaries and packages necessary for running FLASH-TV and Home Assistant on the Jetsons\*

# FLASH-TV In-Home Data Collection
Please see the [checklist](https://docs.google.com/document/d/1YsyBKnJgQ7WB-XFTUHe-cB27ZMZT5CRpLUyl3zfOLHs/) and [slides](https://bcmedu-my.sharepoint.com/:f:/g/personal/207282_bcm_edu/EqhtrTeGWm9DqhoshCBtBtUB0J5otZWmKRoay09M_0a9Hw?e=gyoOaa) for detailed instructions. The checklist is also hosted as a [pdf](./FLASH-TV_In-Home_Installation_Checklist.pdf) in this repository and updated periodically.
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
- [Home_Assistant_Usage.pdf](./Home_Assistant_Usage.pdf)
  > Instructions for setting up Home Assistant manually after installation as the process cannot be automated at the moment
