import subprocess
import colorama
import argparse
import pathlib
import sys
import os

PATH = pathlib.Path(__file__).parent.absolute()
os.chdir(PATH)


COLORS = {
    "R": colorama.Fore.RED,
    "G": colorama.Fore.GREEN,
    "Y": colorama.Fore.YELLOW,
    "RESET": colorama.Fore.RESET,
}


def make_image() -> None:
    subprocess.run('docker', args=['build', '--no-cache', '-t', 'BTBMT', '.'], shell=True)

def delete_image() -> None:
    subprocess.run('docker', args=['rmi', '-f', 'BTBMT'], shell=True)

def update_image() -> None:
    delete_image()
    make_image()



def auto_run() -> None:
    print(f"{COLORS['Y']}[*] Setting things up for docker...{COLORS['RESET']}")
    try:
        subprocess.run('docker', args=['image', 'inspect', 'BTBMT'], check=True)
        update_image()

    except Exception as e:
        make_image()


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-m', '--make-image',
        help="Create a docker image for the bot.", action="store_true"
    )
    parser.add_argument(
        '-u', '--update-image',
        help="Update the docker image for the bot.", action="store_true"
    )
    parser.add_argument(
        '-D', '--delete-image',
        help="Delete the docker image for the bot.", action="store_true"
    )

    args = parser.parse_args()

    if not any([args.update_image, args.delete_image, args.make_image]):
        auto_run()
        return

    if args.update_image and not (args.delete_image or args.make_image):
        update_image()

    elif args.delete_image and not args.update_image:
        delete_image()

    elif args.make_image:
        make_image()


if __name__ == "__main__":
    main()
