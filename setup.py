#!/usr/bin/env python
# pylint: skip-file

import subprocess
import colorama
import pathlib
import logging
import shutil
import sys
import os


PATH = pathlib.Path(__file__).parent.parent.absolute()
os.chdir(PATH)


def input_copy_file(dest: str, message: str):
    try:
        src = input(message)
        shutil.copyfile(src, dest)
        logging.info(f"[+] Found the file {src}!")
    except Exception as e:
        logging.error(f"[-] Couldn't find the file: {src}\nPlease set it up.")

def set_docker_up():
    docker = input("[*] Would you like to perform a setup for docker as well(y/n)?: ")
    if docker in ['y', 'Y']:
        token = input("[*] Enter token: ")
        usr_id = input("[*] Enter User ID: ")
        subprocess.run(f"$(which python3) docker_setup.py -t=\"{token}\ -u=\"{usr_id}\"")

    elif docker in ['n', 'N']:
        print("[*] Skipping docker setup...\nPlease refer to the project docs"
              "for instructions to setup for running the bot in a docker container"
        )

def main():
    if not os.isdir("binance-trade-bot"):
        os.system('git clone https://github.com/edeng23/binance-trade-bot')

    isBTB = input('[*] Is there a BTB installation on your filesystem (y/n)?: ')
    if isBTB in ['y', 'Y']:

        input_copy_file("binance-trade-bot/user.cfg",
                        "[+] Enter path to user.cfg file: ")

        input_copy_file("binance-trade-bot/supported_coin_list",
                        "[+] Enter the path to supported_coin_list: ")

        input_copy_file("binance-trade-bot/config/apprise.yml",
                        "[+] Enter the path to apprise.yml file: ")


    elif isBTB in ['n', 'N']:

        print('''[*] Please manually create the files:
              binance-trade-bot/user.cfg
              binance-trade-bot/supported_coin_list
              binance-trade-bot/config/apprise.yml''')

    else:
        sys.exit(-1)

    set_docker_up()

    print("[*] All set!")


if __name__ == '__main__':
    main()
