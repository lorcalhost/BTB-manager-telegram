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

parser.add_argument(
    "-t", "--token", type=str, help="(optional) Telegram bot token", default=None
)
parser.add_argument(
    "-u", "--user_id", type=str, help="(optional) Telegram user id", default=None
)

args = parser.parse_args()

tok_str = f", \"--token={args.token}\"" if args.token else ""
usr_str = f", \"--user_id={args.user_id}\"" if args.user_id else ""

DOCKERFILE = f'''
###################################################################
# Dockerfile to build container image of:
#   - BTB-manager-telegram
###################################################################

FROM python:3

WORKDIR ./

############ Copying requirements.txt into the container ##########
COPY requirements.txt ./

#################### Installing dependencies ######################
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

################## Running the main python Script #################
CMD [ "python", "-m", "btb_manager_telegram"{tok_str}{usr_str} ]
'''


with open('Dockerfile', "w") as f:
    f.write(DOCKERFILE)
