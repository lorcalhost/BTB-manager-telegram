import hashlib
import hmac
import time
from urllib.parse import urlencode
import os
from configparser import ConfigParser
from binance import Client


from btb_manager_telegram import (
    settings,
)

import requests


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

    url = f'{base_url}{url_path}?{query_string}&signature="{hashing(secret, query_string)}'
    print(f"{http_method} {url}")
    params = {"url": url, "params": {}}
    response = dispatch_request(key, http_method)(**params)
    return response.json()


def get_current_price(ticker, bridge):
    response = requests.get(
        f"https://api.binance.com/api/v3/avgPrice?symbol={ticker}{bridge}"
    ).json()
    return eval(response["price"])


def get_wallet_balance():
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    with open(user_cfg_file_path) as cfg:
        config = ConfigParser()
        config.read_file(cfg)
        api_key = config.get("binance_user_config", "api_key")
        api_secret_key = config.get("binance_user_config", "api_secret_key")

        client = Client(api_key, api_secret_key)

        client.API_URL = "https://api.binance.com/api"
    balances = [
        coin
        for coin in client.get_account()["balances"]
        if coin["free"] != "0.00000000" and coin["free"] != "0.00"
    ]
    for item in balances:
        try:
            if item["asset"] == "USDT" or item["asset"] == "BUSD":
                item["totalInUSD"] = round(float(item["free"]), 2)
            priceToBTC = client.get_avg_price(symbol=item["asset"] + "BTC")["price"]
            item["totalInBTC"] = round(float(priceToBTC), 8) * round(
                float(item["free"]), 8
            )
            btcusd = client.get_avg_price(symbol="BTCUSDT")["price"]
            total = float(btcusd) * float(item["totalInBTC"])
            item["totalInUSD"] = round(total, 2)
        except Exception as e:
            print(item["asset"] + " set to value * 1.00")

    walletInusd = []
    for item in balances:
        if "totalInUSD" in item:
            walletInusd.append(item["totalInUSD"])

    return {
        "timestamp": client.get_account()["updateTime"] / 1000.0,
        "walletInusd": sum(walletInusd),
        "individualCoins": balances,
    }
