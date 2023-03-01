# FLASH-TV Scripts

> FLASH-TV installation, setup, configuration, and runtime scripts

<img src="pngs/teaser_small.png"/>

## INSTRUCTIONS.txt
Instructions for running all the scripts properly, WIP

## full_initial_configuration.sh
Bash script that automatically runs or sets up other bash scripts for procedures marked with an asterisk(\*), needs to be run once on every new Jetson

## runtime_scripts
Bash scripts for running initial FLASH-TV protocols for setup, including building the gallery, creating faces, and running TV gaze estimation with images saved

## install_scripts
Bash scripts for installing ML libaries and packages necessary for running FLASH-TV and Home Assistant on the Jetsons\*

> Make sure you have downloaded the necessary software (insight_face, darknet_face_release etc.) and placed them in the right locations\*(placement only)

## setup_scripts
Bash scripts for the initial setup of the Jetsons in order to be able to run the other scripts and services and properly save data\*

## services
Services for systemd and bash scripts that will run FLASH-TV and Home Assistant on boot and restart FLASH-TV periodically\*

> Start and check status of all services quickly with test_services.sh if necessary
> 
> Disable and stop all services quickly with stop_services.sh if necessary

## python_scripts
Python scripts for running FLASH-TV detection, recognition, and gaze estimation algorithms

## video_capture_scripts
Bash scripts only used on laptop for camera video verification, deleted on Jetsons during setup\*(deletion only)

## participant_change.sh 
Bash script that automatically runs other bash scripts for changing the setup (IDs, services) when changing participants

## homeassistant_setup.txt
Instructions for setting up Home Assistant manually after installation as the process cannot be automated at the moment

