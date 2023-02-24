#do not rerun these commands to start homeassistant, see homeassistant_usage.sh for how to initialize homeassistant after this

#for Python 3.10 easy install
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

#install homeassistant dependencies
sudo apt install -y python3.10 python3.10-dev python3.10-venv python3-pip bluez libffi-dev libssl-dev libjpeg-dev zlib1g-dev autoconf build-essential libopenjp2-7 libtiff5 libturbojpeg0-dev tzdata

#install dbus-broker dependencies
#sudo apt install -y git ninja-build pkg-config python-docutils libsystemd-dev

#meson 1.0 required for dbus-broker install, necessary to do it this way because Ubuntu 20.04 only supports meson 0.53 with apt
#sudo pip3 install meson --upgrade

sudo apt upgrade -y

#download dbus-broker source and build
#cd ~
#git clone https://github.com/bus1/dbus-broker
#cd dbus-broker 
#mkdir build
#cd build/
#meson setup . ..
#ninja
#ninja test
#ninja install

# enable dbus-broker
#systemctl enable dbus-broker.service
#may be necessary also
#sudo systemctl --global enable dbus-broker.service

#add new user for homeassistant
#sudo useradd -rm homeassistant

#set up homeassistant folder
cd ~
mkdir ha

#add and set password for homeassistant sudo just in case, do these commands as flashsysxxx user (I used flash123)
#sudo usermod -aG sudo homeassistant
#sudo passwd homeassistant 

#go to homeassistant directory
cd ha

#sudo chmod -R 777 ha

#create Python 3.10 virtual environment and activate it 
python3.10 -m venv .
source bin/activate

#install Python dependencies and then homeassistant
pip install --upgrade pip
pip3 install wheel
pip3 install homeassistant

#sudo chmod -R 777 ha

#reboot the system after the above
#reboot
