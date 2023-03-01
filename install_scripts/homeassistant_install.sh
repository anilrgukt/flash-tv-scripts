#!/bin/bash
#see homeassistant_setup.txt for how to initialize homeassistant after this

#for Python 3.10 easy install
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update

#install homeassistant dependencies
sudo apt-get install -y python3.10 python3.10-dev python3.10-venv python3-pip bluez libffi-dev libssl-dev libjpeg-dev zlib1g-dev autoconf build-essential libopenjp2-7 libtiff5 libturbojpeg0-dev tzdata

#set up homeassistant folder
cd /home/$USER
mkdir ha

#go to homeassistant directory
cd ha

#create Python 3.10 virtual environment if it doesn't already exist and activate it 
if ! ls | grep -q "bin"
then 
	python3.10 -m venv .
fi
source bin/activate

#install Python dependencies and then homeassistant
pip install --upgrade pip
pip3 install wheel
pip3 install homeassistant
