#!/usr/bin/env python
# pylint: skip-file

import shutil
import logging
import os, sys
import pathlib

PATH = pathlib.Path(__file__).parent.parent.absolute()
os.chdir(PATH)

if not os.path.isdir('config'):
    os.mkdir('config', 0o755)

os.system('git submodule update --init --recursive')


def input_copy_file(dest: str, message: str):
    try:
        src = input(message)
        shutil.copyfile(src, dest)
    except Exception as e:
        logging.error(f'{e}\n')

        sys.exit(1)


input_copy_file("config/user.config",
                "[+] Enter path to user.cfg file: ")

input_copy_file("config/supported_coin_list",
                "[+] Enter the path to supported_coin_list: ")

input_copy_file("config/apprise.yml",
                "[+] Enter the path to apprise.yml file: ")


print("[*] All set!")
