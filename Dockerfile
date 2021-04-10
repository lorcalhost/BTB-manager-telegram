
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
CMD [ "python", "-m", "btb_manager_telegram", "-p", "./binance-trade-bot/"]
