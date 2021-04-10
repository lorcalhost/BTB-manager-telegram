#!/usr/bin/env python
# pylint: skip-file

import subprocess
import colorama
import pathlib
import logging
import shutil
import shlex
import sys
import os


PATH = pathlib.Path(__file__).parent.absolute()
os.chdir(PATH)

COLORS = {
    "R"     : colorama.Fore.RED,
    "G"     : colorama.Fore.GREEN,
    "Y"     : colorama.Fore.YELLOW,
    "RESET" : colorama.Fore.RESET,
}

def input_copy_file(dest: str, message: str):
    try:
        src = input(message).strip()
        shutil.copyfile(src, dest)
        print(f"{COLORS['G']}\n[+] Found the file {src}!{COLORS['RESET']}")
    except Exception as e:
        print(f"{COLORS['R']}\n[-] Couldn't find the file: {src} "
                      f"Please set it up.{COLORS['RESET']}")

def main():
    if not os.path.isdir("binance-trade-bot"):
        os.system('git clone https://github.com/edeng23/binance-trade-bot')

    isBTB = input(f"{COLORS['Y']}[*] Is there a BTB installation on your filesystem (y/n)?: ")
    if isBTB in ['y', 'Y']:

        input_copy_file("binance-trade-bot/user.cfg",
                        f"{COLORS['G']}\n[+] Enter path to user.cfg file: {COLORS['RESET']}")

        input_copy_file("binance-trade-bot/supported_coin_list",
                        f"{COLORS['G']}\n[+] Enter the path to supported_coin_list: {COLORS['RESET']}")

        input_copy_file("binance-trade-bot/config/apprise.yml",
                        f"{COLORS['G']}\n[+] Enter the path to apprise.yml file: {COLORS['RESET']}")


    elif isBTB in ['n', 'N']:

        print(f"""{COLORS['Y']}[*] Please manually create the files:
              binance-trade-bot/user.cfg
              binance-trade-bot/supported_coin_list
              binance-trade-bot/config/apprise.yml\n""")


    docker = input(f"[*] Would you like to run the setup script for"
                   " running the bot in a docker container (y/n)?")

    if docker in ['y', 'Y']:
        command = shlex.split('python3 docker_setup.py')
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE)
            process.communicate()

        except KeyboardInterrupt:
            process.kill()

        except Exception as e:
            print(f"{COLORS['R']}[-] {e} {COLORS['RESET']}")

    else:
        print(f"[*] Skipping te setup for dockerizing the bot{COLORS['RESET']}")
        return
    
    print(f"{COLORS['G']}[*] All set!{COLORS['RESET']}")


if __name__ == '__main__':
    main()
