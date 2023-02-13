

sudo apt-get install screen htop cheese 


# Create a venv 
/home/$user/py38
activate the virtual env
source ~/py38/bin/activate

# use 
numpy=='1.21.2'

#### PYTORCH installation 
# visit https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html

export TORCH_INSTALL=https://developer.download.nvidia.com/compute/redist/jp/v502/pytorch/torch-1.13.0a0+936e9305.nv22.11-cp38-cp38-linux_aarch64.whl

pip install torchvision

#### MXNET installation 
# check instructions at https://mxnet.apache.org/versions/1.9.1/get_started/jetson_setup

# install mxnet - use the below version
in /home/$user
git clone --recursive -b v1.6.x https://github.com/apache/mxnet.git mxnet

# export all the paths mentioned in the installation instructions to ~/.bashrc
source ~/.bashrc

cp /harddisk/FLASH_TV_installation/mxnet_config.mk /home/$user/mxnet

in /home/$user/mxnet
make -j12

# remember to install the python bindings

#### INSIGHTFACE installation
source ~/py38/bin/activate
cd /home/user/insightface/python-package/ 
python setup.py install 

cd /home/user/insightface/detection/retinaface/
make 


#### DARKNET face release installatoin
source ~/py38/bin/activate
cd /home/user/FLASH_TV/darknet_face_release
make clean
make all

sudo apt-get install libxcb-xinerama0





