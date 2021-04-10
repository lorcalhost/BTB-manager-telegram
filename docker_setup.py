import argparse
import os
import pathlib
import shlex
import shutil
import subprocess

import colorama

SUBPIPE = subprocess.PIPE
COLORS = {
    "R": colorama.Fore.RED,
    "G": colorama.Fore.GREEN,
    "Y": colorama.Fore.YELLOW,
    "RESET": colorama.Fore.RESET,
}

PATH = pathlib.Path(__file__).parent.absolute()
os.chdir(PATH)


def delete_image() -> None:
    try:
        command = shlex.split("docker rmi -f btbmt")
        process = subprocess.Popen(command, stderr=SUBPIPE, stdin=SUBPIPE)
        stderr = process.communicate()
        if stderr[1] == b"Error: No such image: btbmt\n":
            print(f"{COLORS['R']}[-] Error: No such image: btbmt{COLORS['RESET']}")

    except KeyboardInterrupt:
        process.kill()


def make_image() -> None:
    command = shlex.split("docker image inspect btbmt")
    check_process = subprocess.Popen(
        command, stdout=SUBPIPE, stderr=SUBPIPE, stdin=SUBPIPE
    )
    out, err = check_process.communicate()
    if out == b"[]\n":
        command = shlex.split("docker build --no-cache -t btbmt .")

        try:
            make_process = subprocess.Popen(command, stdin=SUBPIPE)
            make_process.communicate()

        except KeyboardInterrupt:
            make_process.kill()

    else:
        make_new = input(
            f"{COLORS['Y']}[*] A docker image already exists "
            f"Do you wish to update it(y/n)?: "
        )

        if make_new in ["y", "Y"]:
            print(f"[*] Updating the image...{COLORS['RESET']}")
            update_image()


def update_image() -> None:
    delete_image()
    make_image()


def docker_setup() -> None:
    print(f"{COLORS['Y']}[*] Setting things up for docker...{COLORS['RESET']}")
    command = shlex.split("docker image inspect btbmt")

    try:
        process = subprocess.Popen(
            command, stdout=SUBPIPE, stderr=SUBPIPE, stdin=SUBPIPE
        )
        process.communicate()

    except KeyboardInterrupt:
        process.kill()

    except Exception:
        make_image()

    finally:
        update_image()


def color_copy_file(src: str, dest: str):
    try:
        shutil.copyfile(src, dest)
        print(f"{COLORS['G']}[+] Copying {src} to {dest}{COLORS['RESET']}")
    except Exception:
        print(
            f"{COLORS['R']}[-] Unable to find file {src}\n"
            f"\tPlease manually create it at {dest}{COLORS['RESET']}"
        )


def default() -> None:
    if not os.path.exists("binance-trade-bot"):
        subprocess.call(
            "git clone https://github.com/edeng23/binance-trade-bot >/dev/null",
            shell=True,
        )

    exists_previous_btb_install = input(
        f"{COLORS['Y']}[*] Is a Binance Trade Bot installation already present on your filesystem (y/n)?: {COLORS['RESET']}"
    )

    if exists_previous_btb_install in ["y", "Y"]:
        btb_installation_dir = input(
            f"{COLORS['Y']}[*] Enter path to your previous Binance Trade bot installation (e.g. ../binance-trade-bot/): {COLORS['RESET']}"
        )

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

    elif exists_previous_btb_install in ["n", "N"]:
        print(
            f"{COLORS['Y']}[*] Please manually create/edit the following files:\n"
            f"\t- ./binance-trade-bot/user.cfg\n"
            f"\t- ./binance-trade-bot/supported_coin_list\n"
            f"\t- ./binance-trade-bot/config/apprise.yml"
        )

    docker = input(
        f"{COLORS['Y']}[*] Would you like to run the setup script for running the bot in a docker container (y/n)?: "
    )

    if docker in ["y", "Y"]:
        docker_setup()
        print(f"{COLORS['G']}[*] All set!{COLORS['RESET']}")

    else:
        print(
            f"{COLORS['Y']}[*] Skipping setup for dockerizing the bot{COLORS['RESET']}"
        )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-m",
        "--make-image",
        help="Create a docker image for the bot.",
        action="store_true",
    )
    parser.add_argument(
        "-u",
        "--update-image",
        help="Update the docker image for the bot.",
        action="store_true",
    )
    parser.add_argument(
        "-D",
        "--delete-image",
        help="Delete the docker image for the bot.",
        action="store_true",
    )

    args = parser.parse_args()

    if not any([args.update_image, args.delete_image, args.make_image]):
        default()

    elif args.update_image and not (args.delete_image or args.make_image):
        update_image()

    elif args.delete_image and not args.update_image:
        delete_image()

    elif args.make_image:
        make_image()


if __name__ == "__main__":
    main()
