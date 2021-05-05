import json
import hashlib
import hmac
import os
import subprocess
import sys
import time
import hashlib
from configparser import ConfigParser
from urllib.parse import urlencode
from datetime import datetime

import requests
from typing import List

from btb_manager_telegram import logger, settings


def hashing(secret, query_string):
    return hmac.new(
        secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(key, http_method):
    session = requests.Session()
    session.headers.update(
        {"Content-Type": "application/json;charset=utf-8", "X-MBX-APIKEY": key}
    )
    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


def send_signed_request(key, secret, base_url, http_method, url_path, payload={}):
    query_string = urlencode(payload, True)
    if query_string:
        query_string = f"{query_string}&timestamp={get_timestamp()}"
    else:
        query_string = f"timestamp={get_timestamp()}"

    url = f'{base_url}{url_path}?{query_string}&signature={hashing(secret, query_string)}'
    print(f"{http_method} {url}")
    params = {"url": url, "params": {}}
    response = dispatch_request(key, http_method)(**params)
    return response.json()


def get_current_price(ticker, bridge):
    response = requests.get(
        f"https://api.binance.com/api/v3/avgPrice?symbol={ticker}{bridge}"
    ).json()
    return eval(response["price"])


def jprint(obj):
    # create a formatted string of the Python JSON object
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)


def get_accsnp():
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    with open(user_cfg_file_path) as cfg:
        config = ConfigParser()
        config.read_file(cfg)
        api_key = config.get("binance_user_config", "api_key")
        api_secret_key = config.get("binance_user_config", "api_secret_key")
        tld = config.get("binance_user_config", "tld")
        params = {
            "type": "SPOT",
        }

    try:
        message = send_signed_request(
            api_key,
            api_secret_key,
            f"https://api.binance.{tld}",
            "GET",
            "/sapi/v1/accountSnapshot",
            payload=params,
        )
        code = message['code']
        msg = message['msg']
        if code != 200:
            print(code)
            print(msg)

        snapshotVos = (message['snapshotVos'])
        data = snapshotVos[0]["data"]
        totalAssetOfBtc = data["totalAssetOfBtc"]
        jprint(totalAssetOfBtc)
        balances = data["balances"]
        jprint(balances)
        result = f"{totalAssetOfBtc}BTC     ",
        for bal in balances:
            if bal["free"] != 0:
                asset = bal["asset"]
                free = bal["free"]
                locked = bal["locked"]
                response = f"Asset: {asset} free: {free} locked: {locked}        ",
                result += response


        print(result)
        #result = result.replace(".", "\.")

        return result

    except Exception as e:
        logger.error(f"get_accsnp {e}")
        return [f"get_accsnp {e}"]
