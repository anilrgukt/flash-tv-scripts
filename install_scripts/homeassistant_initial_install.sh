#do not rerun these commands, see homeassistant_usage.sh for how to initialize homeassistant after this
#for Python 3.10 easy install
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

#install homeassistant dependencies
sudo apt install -y python3.10 python3.10-dev python3.10-venv python3-pip bluez libffi-dev libssl-dev libjpeg-dev zlib1g-dev autoconf build-essential libopenjp2-7 libtiff5 libturbojpeg0-dev tzdata

sudo apt upgrade -y

#add new user for homeassistant
sudo useradd -rm homeassistant

#set up homeassistant folder
sudo mkdir /srv/homeassistant
sudo chown homeassistant:homeassistant /srv/homeassistant

#add and set password for homeassistant sudo just in case, do these commands as flashsysxxx user (I used ha123)
usermod -aG sudo homeassistant
sudo passwd homeassistant 

#login to homeassistant account
sudo -u homeassistant -H -s

#go to homeassistant directory
cd /srv/homeassistant

#create Python 3.10 virtual environment and activate it 
python3.10 -m venv .
source bin/activate

#install Python dependencies and then homeassistant
pip install --upgrade pip
pip3 install wheel
pip3 install homeassistant==2023.2.3


#start homeassistant (must be in Python 3.10 venv)
hass 

#NOW open localhost:8123 and create account, detect info but only if at Baylor, then hit next and wait a few minutes, don't select anything for information, don't add any devices. Now we need to setup Bluetooth. Press Ctrl C to close homeassistant and go to flashsysxxx terminal

#install dbus-broker installation dependencies
sudo apt install git ninja-build pkg-config python-docutils libsystemd-dev

#necessary to do it this way because Ubuntu 20.04 only supports meson 0.53 with apt
sudo pip3 install meson --upgrade

#download dbus-broker source and build
cd ~
git clone https://github.com/bus1/dbus-broker
cd dbus-broker 
mkdir build
cd build/
meson setup . ..
ninja
ninja test
ninja install

# enable dbus-broker
systemctl enable dbus-broker.service
#may be necessary also
sudo systemctl --global enable dbus-broker.service

#reboot the system after the above

