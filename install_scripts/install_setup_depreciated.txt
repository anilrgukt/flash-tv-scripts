#DO NOT RUN,DEPRECIATED, USE install_setup_auto.sh

echo "DO NOT RUN, DEPRECIATED, USE install_setup_auto.sh"

#sudo apt install screen htop cheese v4l-utils python3.8-venv virtualenvironment


# Create a venv 
#python3 -m venv /home/$USER/py38
#python3 -m virtualenv -p python3 py38

#activate the virtual env
#source ~/py38/bin/activate

# use numpy=='1.21.2'
# scipy=='1.5.3'???

#### PYTORCH installation 
# visit https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html

#export TORCH_INSTALL=https://developer.download.nvidia.com/compute/redist/jp/v502/pytorch/torch-1.13.0a0+936e9305.nv22.11-cp38-cp38-linux_aarch64.whl

#python3 -m pip install --upgrade pip; python3 -m pip install aiohttp numpy=='1.21.2' scipy=='1.5.3'; export "LD_LIBRARY_PATH=/usr/lib/llvm-8/lib:$LD_LIBRARY_PATH"; python3 -m pip install --upgrade protobuf; python3 -m pip install --no-cache $TORCH_INSTALL; pip install torchvision

#### MXNET installation 
# check instructions at https://mxnet.apache.org/versions/1.9.1/get_started/jetson_setup

#sudo apt update
#sudo apt install -y \
#	build-essential \
#	git \
#	libopenblas-dev \
#	libopencv-dev \
#	python3-pip \
#	python-numpy \
#	python3-testresources \
#	libatlas-base-dev 

#pip install --upgrade \
#	pip \
#	setuptools \
#	Cython \
#	packaging \
#	lazy_loader \
#	imageio \
#	scikit-image

                        
# install mxnet - use the below version
#in /home/$USER
#git clone --recursive -b v1.6.x https://github.com/apache/mxnet.git mxnet

# export all the paths mentioned in the installation instructions to ~/.bashrc
# export PATH=/usr/local/cuda/bin:$PATH
# export MXNET_HOME=$HOME/mxnet/
# export PYTHONPATH=$MXNET_HOME/python:$PYTHONPATH

#source ~/.bashrc

#cp /media/flashsys00x/696f0b73-ad9f-44a2-9cbd-fd09be1e4164/FLASH_TV_installation/mxnet_config.mk /home/$USER/mxnet/config.mk

#cd /home/$USER/mxnet
# maybe needs libatlas-base-dev installed
#make -j12

# remember to install the python bindings
#cd /home/$USER/mxnet/python
#pip3 install -e .

#Copy folders listed in FLASH_filesetup.sh before doing the following 
#### INSIGHTFACE installation
#source ~/py38/bin/activate
#cd /home/$USER/insightface/python-package/ 
#python setup.py install 

#cd /home/$USER/insightface/detection/RetinaFace/
#make 


#### DARKNET face release installation
#source ~/py38/bin/activate
#cd /home/$USER/FLASH_TV/darknet_face_release
#make clean
#make all

# In Python terminal
#import torch
#torch.cuda.is_available()

#import mxnet as mx
#a = mx.nd.ones((2, 3), mx.gpu())
#b = a * 2 + 1
#b.asnumpy()

#pip install numpy=='1.21.2'
