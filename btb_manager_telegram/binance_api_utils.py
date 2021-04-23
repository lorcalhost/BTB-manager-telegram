import hashlib
import hmac
import time
from urllib.parse import urlencode

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
