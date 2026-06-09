#!/bin/bash
# Install the MERlin package on Harvard RC
# Run this script in the home directory of MERlin

conda create --name merlin_python310 python=3.10
conda activate merlin_python310

pip install -e .
