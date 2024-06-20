#!/usr/bin/env bash

pip install virtualenv
virtualenv venv
source venv/bin/activate

apt update
apt install -y vim
apt install -y python3-dev libpq-dev unzip
apt-get -y install intel-mkl htop nvtop swig


pip install medcat
pip install -U tokenizers datasets transformers
pip install optimum auto-gptq


mkdir saved
cd saved || exit
aws s3 cp --recursive s3://geniusrise-test-healthcare/demo-day/ .
