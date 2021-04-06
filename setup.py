################################################################################
import sys, os
import pathlib
import argparse
import subprocess
################################################################################
PATH = pathlib.Path(__file__).parent.absolute()
os.chdir(PATH)
################################################################################

parser = argparse.ArgumentParser()

parser.add_argument("--paths", action="store_true",
                    help="To specify if you want to run the setup process using paths to the config files.")

# TODO: add individual flags that help modify each file and stuffs
# TODO: add a '--all' flag to make the user enter all details

args = parser.parse_args()

if args.paths:
    os.system("$(which python3) setup_scripts/setup_by_path.py")
