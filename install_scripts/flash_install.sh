#!/bin/bash

#### General dependencies
sudo apt-get install -y nvidia-jetpack screen htop cheese v4l-utils python3.8-venv libxcb-xinerama0 nano

#### PYTORCH dependencies
# visit https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html
sudo apt-get install -y \
	build-essential \
	git \
	libopenblas-dev \
	libopencv-dev \
	python3-pip \
	python-numpy \
	python3-testresources \
	libatlas-base-dev 

cd /home/$USER

# Create a venv if it doesn't already exist
if ! ls | grep -q "py38"
then 
	python3 -m venv ~/py38
fi

# Activate the virtual env
source ~/py38/bin/activate

# numpy=='1.21.2'???
# scipy=='1.9.1'???

export TORCH_INSTALL=https://developer.download.nvidia.cn/compute/redist/jp/v51/pytorch/torch-1.14.0a0+44dac51c.nv23.01-cp38-cp38-linux_aarch64.whl

python3 -m pip install --upgrade pip; python3 -m pip install aiohttp numpy=='1.21.4' scipy=='1.9.1'; export "LD_LIBRARY_PATH=/usr/lib/llvm-8/lib:$LD_LIBRARY_PATH"; python3 -m pip install --upgrade protobuf; python3 -m pip install --no-cache $TORCH_INSTALL; pip install torchvision==0.14.1

### RTC Dependencies
pip install smbus2 watchdog

#### MXNET dependencies
# check instructions at https://mxnet.apache.org/versions/1.9.1/get_started/jetson_setup
pip install --upgrade \
	pip \
	setuptools \
	Cython \
	packaging \
	lazy_loader \
	imageio \
	scikit-image

# install mxnet - use the below version

cd /home/$USER
git clone --recursive -b v1.6.x https://github.com/apache/mxnet.git mxnet

# export all the paths mentioned in the installation instructions to ~/.bashrc

PATH1="export PATH=/usr/local/cuda/bin:\$PATH"
PATH2="export MXNET_HOME=\$HOME/mxnet/"
PATH3="export PYTHONPATH=\$MXNET_HOME/python:\$PYTHONPATH"
FILE='.bashrc'
grep -xqF -- "$PATH1" "$FILE" || echo "$PATH1" >> "$FILE"
grep -xqF -- "$PATH2" "$FILE" || echo "$PATH2" >> "$FILE"
grep -xqF -- "$PATH3" "$FILE" || echo "$PATH3" >> "$FILE"

source ~/.bashrc

cp ~/flash-tv-scripts/install_scripts/mxnet_config.mk ~/mxnet/config.mk

cd ~/mxnet
make -j12

# remember to install the python bindings
cd ~/mxnet/python
pip3 install -e .

#Copy folders listed in FLASH_filesetup.sh before doing the following 

#### INSIGHTFACE installation
source ~/py38/bin/activate
cd ~/insightface/python-package/ 
python setup.py install 

cd ~/insightface/detection/RetinaFace/
make -j12

#### DARKNET face release installation
source ~/py38/bin/activate
cd ~/FLASH_TV/darknet_face_release
make clean
make -j12 all

#reboot
