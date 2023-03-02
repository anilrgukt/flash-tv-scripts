# FLASH-TV Scripts

> FLASH-TV installation, setup, configuration, and runtime scripts

<img src="pngs/teaser_small.png"/>

# FLASH-TV Installation on NVIDIA Jetson AGX Orin Devkits
Please read the [INSTRUCTIONS](./INSTRUCTIONS.txt) file above for details
> Make sure you have downloaded or copied the necessary software (insight_face, darknet_face_release etc.) and placed it in the right locations(\*placement only, when specific external hard disk is connected)

 - full_initial_configuration.sh
   > Bash script that automatically runs or sets up other bash scripts for procedures marked with an asterisk(\*), needs to be run once on every new Jetson

 - install_scripts
   > Bash scripts for installing ML libaries and packages necessary for running FLASH-TV and Home Assistant on the Jetsons\*

# FLASH-TV In-Home Data Collection
Please use the [check list](https://docs.google.com/document/d/1YsyBKnJgQ7WB-XFTUHe-cB27ZMZT5CRpLUyl3zfOLHs/) or [pdf](./FLASH-TV_in_home_installation_checklist.pdf) for detailed instructions 
- runtime_scripts
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
- homeassistant_setup.txt
  > Instructions for setting up Home Assistant manually after installation as the process cannot be automated at the moment
