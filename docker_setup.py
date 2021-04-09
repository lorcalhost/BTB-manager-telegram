import os
import pathlib
import shutil
import subprocess
import sys

import colorama

PATH = pathlib.Path(__file__).parent.absolute()
os.chdir(PATH)

COLORS = {
    "R": colorama.Fore.RED,
    "G": colorama.Fore.GREEN,
    "Y": colorama.Fore.YELLOW,
    "RESET": colorama.Fore.RESET,
}


def color_copy_file(src: str, dest: str):
    try:
        shutil.copyfile(src, dest)
        print(f"{COLORS['G']}[+] Copying {src} to {dest}{COLORS['RESET']}")
    except Exception:
        print(
            f"{COLORS['R']}[-] Couldn't find the file: {src}\n"
            f"\tPlease manually create it at {dest}{COLORS['RESET']}"
        )


def main():
    if not os.path.exists("binance-trade-bot"):
        subprocess.call(
            "git clone https://github.com/edeng23/binance-trade-bot >/dev/null",
            shell=True,
        )

    isBTB = input(
        f"{COLORS['Y']}[*] Is a Binance Trade Bot installation already present on your filesystem (y/n)?: {COLORS['RESET']}"
    )
    if isBTB in ["y", "Y"]:
        btb_installation_dir = input(
            f"{COLORS['Y']}[*] Enter path to your previous Binance Trade bot installation (e.g. ../binance-trade-bot/): {COLORS['RESET']}"
        )
        os.path.exists(btb_installation_dir)

        while not os.path.exists(btb_installation_dir):
            btb_installation_dir = input(
                f"{COLORS['R']}[-] Couldn't find the specified path on the filesystem, try again: {COLORS['RESET']}"
            )
        else:
            print(
                f"{COLORS['G']}[+] Path {btb_installation_dir} found on the filesystem.{COLORS['RESET']}"
            )

        color_copy_file(
            os.path.join(btb_installation_dir, "user.cfg"),
            "./binance-trade-bot/user.cfg",
        )
        color_copy_file(
            os.path.join(btb_installation_dir, "supported_coin_list"),
            "./binance-trade-bot/supported_coin_list",
        )
        color_copy_file(
            os.path.join(btb_installation_dir, "config/apprise.yml"),
            "./binance-trade-bot/config/apprise.yml",
        )

    elif isBTB in ["n", "N"]:

        print(
            f"{COLORS['Y']}[*] Please manually create/edit the following files:\n"
            f"\t./binance-trade-bot/user.cfg\n"
            f"\t./binance-trade-bot/supported_coin_list\n"
            f"\t./binance-trade-bot/config/apprise.yml"
        )

    else:
        sys.exit(-1)

    print(f"{COLORS['G']}[*] All set!{COLORS['RESET']}")


if __name__ == "__main__":
    main()
