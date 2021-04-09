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

COLORS = {
    "R"     : colorama.Fore.RED,
    "G"     : colorama.Fore.GREEN,
    "Y"     : colorama.Fore.YELLOW,
    "RESET" : colorama.Fore.RESET,
}

def input_copy_file(dest: str, message: str):
    try:
        src = input(message)
        shutil.copyfile(src, dest)
        logging.info(f"{COLORS['G']}[+] Found the file {src}!{COLORS['RESET']}")
    except Exception as e:
        logging.error(f"{COLORS['R']}[-] Couldn't find the file: {src}"
                      f"Please set it up.{COLORS['RESET']}")

def set_docker_up():
    docker = input(f"{COLORS['Y']}[*] Would you like to perform a setup for docker as well(y/n)?: ")
    if docker in ['y', 'Y']:
        token = input(f"{COLORS['G']}[+] Enter token: ")
        usr_id = input(f"{COLORS['G']}[+] Enter User ID: ")
        subprocess.run(f"$(which python3) docker_setup.py -t=\"{token}\ -u=\"{usr_id}\"")

    elif docker in ['n', 'N']:
        print(f"{COLORS['Y']}[*] Skipping docker setup...\nPlease refer to the project docs"
              "for instructions to setup for running the bot in a docker container"
        )

def main():
    if not os.isdir("binance-trade-bot"):
        os.system('git clone https://github.com/edeng23/binance-trade-bot')

    isBTB = input(f'{COLORS['Y']}[*] Is there a BTB installation on your filesystem (y/n)?: ')
    if isBTB in ['y', 'Y']:

        input_copy_file("binance-trade-bot/user.cfg",
                        f"{COLORS['G']}[+] Enter path to user.cfg file: ")

        input_copy_file("binance-trade-bot/supported_coin_list",
                        f"{COLORS['G']}[+] Enter the path to supported_coin_list: ")

        input_copy_file("binance-trade-bot/config/apprise.yml",
                        f"{COLORS['G']}[+] Enter the path to apprise.yml file: ")


    elif isBTB in ['n', 'N']:

        print(f'''{COLORS['Y']}[*] Please manually create the files:
              binance-trade-bot/user.cfg
              binance-trade-bot/supported_coin_list
              binance-trade-bot/config/apprise.yml''')

    else:
        sys.exit(-1)

    set_docker_up()

    print(f"[*] All set!{COLORS['RESET']}")


if __name__ == '__main__':
    main()
