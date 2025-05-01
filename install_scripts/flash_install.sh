#!/bin/bash

### General Package Dependencies ###

sudo apt-get install -y nvidia-jetpack screen htop cheese v4l-utils python3.8-venv libxcb-xinerama0 nano gimp libbluetooth-dev

### USB Backup Package Dependencies ###

sudo apt-get install -y borgbackup

### PyTorch Package Dependencies ###

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

cd "${HOME}" || exit 1

# Create a Python 3.8 vjrtual environment if it doesn't already exist

if [ ! -d "py38" ]; then
	python3 -m venv "${HOME}/py38"
fi

# Activate the virtual environment

# shellcheck source=/dev/null
source "${HOME}/py38/bin/activate"

### RTC Python Dependencies ###

pip install smbus2 watchdog

### USB Backup Python Dependencies ### 

pip install cryptography --upgrade

### PyTorch Python Dependencies ###

export TORCH_INSTALL="https://developer.download.nvidia.cn/compute/redist/jp/v51/pytorch/torch-1.14.0a0+44dac51c.nv23.01-cp38-cp38-linux_aarch64.whl"

python3 -m pip install --upgrade pip

# numpy=='1.21.2'???
# scipy=='1.9.1'???

python3 -m pip install aiohttp numpy=='1.21.4' scipy=='1.9.1'

export LD_LIBRARY_PATH="/usr/lib/llvm-8/lib:${LD_LIBRARY_PATH}"

python3 -m pip install --upgrade protobuf

python3 -m pip install --no-cache ${TORCH_INSTALL}

pip install torchvision==0.14.1

### MXNet Python Dependencies ###

# check instructions at https://mxnet.apache.org/versions/1.9.1/get_started/jetson_setup

pip install --upgrade \
	pip \
	setuptools \
	Cython \
	packaging \
	lazy_loader \
	imageio \
	scikit-image \
	opencv-python \
	tqdm

# Install mxnet - use the below version

cd "${HOME}" || exit 1
git clone --recursive -b v1.6.x https://github.com/apache/mxnet.git mxnet

# Export all the paths mentioned in the installation instructions to "${HOME}/.bashrc"

PATH1="export PATH=/usr/local/cuda/bin:\${PATH}"
PATH2="export MXNET_HOME=\${HOME}/mxnet/"
PATH3="export PYTHONPATH=\${MXNET_HOME}/python:\${PYTHONPATH}"
FILE='.bashrc'
grep -xqF -- "${PATH1}" "${FILE}" || echo "${PATH1}" >>"${FILE}"
grep -xqF -- "${PATH2}" "${FILE}" || echo "${PATH2}" >>"${FILE}"
grep -xqF -- "${PATH3}" "${FILE}" || echo "${PATH3}" >>"${FILE}"

# shellcheck source=/dev/null
source "${HOME}/.bashrc"

cp "${HOME}/flash-tv-scripts/install_scripts/mxnet_config.mk" "${HOME}/mxnet/config.mk"

cd "${HOME}/mxnet" || exit 1

make clean

make -j12 all

# Install the MXNet Python bindings
cd "${HOME}/mxnet/python" || exit 1

pip3 install -e .

# Copy folders listed in file_setup.sh before doing the following

### InsightFace Installation ###

# shellcheck source=/dev/null
source "${HOME}/py38/bin/activate"

cd "${HOME}/insightface/python-package/" || exit 1

python "setup.py" install

cd "${HOME}/insightface/detection/RetinaFace/" || exit 1

make clean

make -j12 all

### darknet Face Release Installation ###

# shellcheck source=/dev/null
source "${HOME}/py38/bin/activate"

cd "${HOME}/FLASH_TV/darknet_face_release" || exit 1

make clean

make -j12 all

exit 0
