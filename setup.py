#!/usr/bin/env python
# pylint: skip-file

import subprocess
import shutil
import argparse
import logging
import os, sys
import pathlib

PATH = pathlib.Path(__file__).parent.absolute()
os.chdir(PATH)

if not os.path.isdir('config'):
    os.system('mkdir config')

if not os.path.isfile('config/user_config.json'):
    os.system('touch config/user_config.json')

os.system('git submodule update --init --recursive')
