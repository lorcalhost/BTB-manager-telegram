# -*- coding: utf-8 -*-
import os
import sqlite3
from datetime import datetime


class SQLiteQuery:
    def __init__(self, root_path):
        self.root_path = root_path

    def get_current_value_message(self):
        db_file_path = f"{self.root_path}data/crypto_trading.db"
        message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
        if os.path.exists(db_file_path):
            try:
                con = sqlite3.connect(db_file_path)
                cur = con.cursor()

                # Get current coin symbol, bridge symbol, order state, order size, initial buying price
                try:
                    cur.execute(
                        """SELECT alt_coin_id, crypto_coin_id, state, crypto_starting_balance, crypto_trade_amount FROM trade_history ORDER BY datetime DESC LIMIT 1;"""
                    )
                    current_coin, bridge, state, order_size, buy_price = cur.fetchone()
                    if current_coin is None:
                        raise Exception()
                    if state == "ORDERED":
                        return [
                            f"A buy order of `{round(order_size, 2)}` *{bridge}* is currently placed on coin *{current_coin}*.\n\n_Waiting for buy order to complete_.".replace(
                                ".", "\."
                            )
                        ]
                except:
                    con.close()
                    return [f"❌ Unable to fetch current coin from database\."]

                # Get balance, current coin price in USD, current coin price in BTC
                try:
                    cur.execute(
                        f"""SELECT balance, usd_price, btc_price, datetime FROM 'coin_value' WHERE coin_id = '{current_coin}' ORDER BY datetime DESC LIMIT 1;"""
                    )
                    balance, usd_price, btc_price, last_update = cur.fetchone()
                    if balance is None:
                        balance = 0
                    if usd_price is None:
                        usd_price = 0
                    if btc_price is None:
                        btc_price = 0
                    last_update = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S.%f")
                except:
                    con.close()
                    return [
                        f"❌ Unable to fetch current coin information from database\.",
                        f"⚠ If you tried using the `Current value` button during a trade please try again after the trade has been completed\.",
                    ]

                # Generate message
                try:
                    message = [
                        f'\nLast update: `{last_update.strftime("%H:%M:%S %d/%m/%Y")}`\n\n*Current coin {current_coin}:*\n\t\- Balance: `{round(balance, 6)}` {current_coin}\n\t\- Value in *USD*: `{round((balance * usd_price), 2)}` $\n\t\- Value in *BTC*: `{round((balance * btc_price), 6)}` BTC\n\n\t_Initially bought for_ {round(buy_price, 2)} *{bridge}*\n'.replace(
                            ".", "\."
                        )
                    ]
                    con.close()
                except:
                    con.close()
                    return [
                        f"❌ Something went wrong, unable to generate value at this time\."
                    ]
            except:
                message = ["❌ Unable to perform actions on the database\."]
        return message
