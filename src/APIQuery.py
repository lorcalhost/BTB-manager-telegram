# -*- coding: utf-8 -*-
import json
from datetime import datetime

import requests


class APIQuery:
    def __init__(self):
        self.base_url = "http://0.0.0.0:5123"

    def is_available(self):
        return True if self.__trade_history() is not False else False

    def __trade_history(self):
        try:
            re = json.loads(requests.get(f"{self.base_url}/api/trade_history").content)
        except:
            re = False
        return re

    def __value_history(self, coin):
        try:
            re = json.loads(
                requests.get(f"{self.base_url}/api/value_history/{coin}").content
            )
        except:
            re = False
        return re

    def get_current_value_message(self):
        # Get current coin symbol, bridge symbol, order state, order size, initial buying price
        th = self.__trade_history()
        if th is not False:
            c = sorted(th, key=lambda k: k["datetime"], reverse=True)[0]
            current_coin = c["alt_coin"]["symbol"]
            bridge = c["crypto_coin"]["symbol"]
            state = c["state"]
            order_size = c["crypto_starting_balance"]
            buy_price = c["crypto_trade_amount"]
            if state == "ORDERED":
                return [
                    f"A buy order of `{round(order_size, 2)}` *{bridge}* is currently placed on coin *{current_coin}*.\n\n_Waiting for buy order to complete_.".replace(
                        ".", "\."
                    )
                ]
        else:
            return [f"❌ Unable to fetch current coin from database\."]

        # Get balance, current coin price in USD, current coin price in BTC
        vh = self.__value_history(current_coin)
        if vh is not False:
            d = sorted(vh, key=lambda k: k["datetime"], reverse=True)[0]
            balance = 0 if d["balance"] is None else d["balance"]
            usd_value = 0 if d["usd_value"] is None else d["usd_value"]
            btc_value = 0 if d["btc_value"] is None else d["btc_value"]
            last_update = datetime.strptime(d["datetime"], "%Y-%m-%dT%H:%M:%S.%f")
        else:
            return [
                f"❌ Unable to fetch current coin information from database\.",
                f"⚠ If you tried using the `Current value` button during a trade please try again after the trade has been completed\.",
            ]

        # Generate message
        try:
            m_list = [
                f'\nLast update: `{last_update.strftime("%H:%M:%S %d/%m/%Y")}`\n\n*Current coin {current_coin}:*\n\t\- Balance: `{round(balance, 6)}` {current_coin}\n\t\- Value in *USD*: `{round(usd_value, 2)}` $\n\t\- Value in *BTC*: `{round(btc_value, 6)}` BTC\n\n\t_Initially bought for_ {round(buy_price, 2)} *{bridge}*\n'.replace(
                    ".", "\."
                )
            ]
        except:
            m_list = [
                f"❌ Something went wrong, unable to generate value at this time\."
            ]
        return m_list
