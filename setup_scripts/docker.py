import subprocess
import colorama
import argparse
import shlex

SUBPIPE = subprocess.PIPE
COLORS = {
    "R": colorama.Fore.RED,
    "G": colorama.Fore.GREEN,
    "Y": colorama.Fore.YELLOW,
    "RESET": colorama.Fore.RESET,
}


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


def auto_run() -> None:
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


def main() -> None:
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
        auto_run()
        return

    if args.update_image and not (args.delete_image or args.make_image):
        update_image()

    elif args.delete_image and not args.update_image:
        delete_image()

    elif args.make_image:
        make_image()
