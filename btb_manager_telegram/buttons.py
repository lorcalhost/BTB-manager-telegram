import os
import sqlite3
import subprocess
from configparser import ConfigParser
from datetime import datetime

from btb_manager_telegram import logger, settings
from btb_manager_telegram.utils import find_process, text_4096_cutter


def current_value():
    logger.info("Current value button pressed.")

    db_file_path = f"{settings.ROOT_PATH}data/crypto_trading.db"
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
                query = cur.fetchone()
                if query is None:
                    return [
                        f"❌ No information about *{current_coin}* available in the database\.",
                        f"⚠ If you tried using the `Current value` button during a trade please try again after the trade has been completed\.",
                    ]
                balance, usd_price, btc_price, last_update = query
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
                m_list = [
                    f'\nLast update: `{last_update.strftime("%H:%M:%S %d/%m/%Y")}`\n\n*Current coin {current_coin}:*\n\t\- Balance: `{round(balance, 6)}` {current_coin}\n\t\- Value in *USD*: `{round((balance * usd_price), 2)}` *USD*\n\t\- Value in *BTC*: `{round((balance * btc_price), 6)}` BTC\n\n\t_Initially bought for_ {round(buy_price, 2)} *{bridge}*\n'.replace(
                        ".", "\."
                    )
                ]
                message = text_4096_cutter(m_list)
                con.close()
            except:
                con.close()
                return [
                    f"❌ Something went wrong, unable to generate value at this time\."
                ]
        except:
            message = ["❌ Unable to perform actions on the database\."]
    return message


def check_progress():
    logger.info("Progress button pressed.")

    db_file_path = f"{settings.ROOT_PATH}data/crypto_trading.db"
    user_cfg_file_path = f"{settings.ROOT_PATH}user.cfg"
    message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
    if os.path.exists(db_file_path):
        try:
            con = sqlite3.connect(db_file_path)
            cur = con.cursor()

            # Get progress information
            try:
                cur.execute(
                    """SELECT th1.alt_coin_id AS coin, th1.alt_trade_amount AS amount, th1.crypto_trade_amount AS priceInUSD,(th1.alt_trade_amount - ( SELECT th2.alt_trade_amount FROM trade_history th2 WHERE th2.alt_coin_id = th1.alt_coin_id AND th1.datetime > th2.datetime AND th2.selling = 0 ORDER BY th2.datetime DESC LIMIT 1)) AS change, datetime FROM trade_history th1 WHERE th1.state = 'COMPLETE' AND th1.selling = 0 ORDER BY th1.datetime DESC LIMIT 15"""
                )
                query = cur.fetchall()

                # Generate message
                m_list = [f"Current coin amount progress:\n\n"]
                for coin in query:
                    last_trade_date = datetime.strptime(
                        coin[4], "%Y-%m-%d %H:%M:%S.%f"
                    ).strftime("%H:%M:%S %d/%m/%Y")
                    m_list.append(
                        f'*{coin[0]}*\n\t\- Amount: `{round(coin[1], 6)}` *{coin[0]}*\n\t\- Price: `{round(coin[2], 2)}` *USD*\n\t\- Change: {f"`{round(coin[3], 2)}` *{coin[0]}*" if coin[3] is not None else f"`{coin[3]}`"}\n\t\- Last trade: `{last_trade_date}`\n\n'.replace(
                            ".", "\."
                        )
                    )

                message = text_4096_cutter(m_list)
                con.close()
            except:
                con.close()
                return [f"❌ Unable to fetch progress information from database\."]
        except:
            message = ["❌ Unable to perform actions on the database\."]
    return message


def current_ratios():
    logger.info("Current ratios button pressed.")

    db_file_path = f"{settings.ROOT_PATH}data/crypto_trading.db"
    user_cfg_file_path = f"{settings.ROOT_PATH}user.cfg"
    message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
    if os.path.exists(db_file_path):
        try:
            # Get bridge currency symbol
            with open(user_cfg_file_path) as cfg:
                config = ConfigParser()
                config.read_file(cfg)
                bridge = config.get("binance_user_config", "bridge")

            con = sqlite3.connect(db_file_path)
            cur = con.cursor()

            # Get current coin symbol
            try:
                cur.execute(
                    """SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1;"""
                )
                current_coin = cur.fetchone()[0]
                if current_coin is None:
                    raise Exception()
            except:
                con.close()
                return [f"❌ Unable to fetch current coin from database\."]

            # Get prices and ratios of all alt coins
            try:
                cur.execute(
                    f"""SELECT sh.datetime, p.to_coin_id, sh.other_coin_price, ( ( ( current_coin_price / other_coin_price ) - 0.001 * 5 * ( current_coin_price / other_coin_price ) ) - sh.target_ratio ) AS 'ratio_dict' FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id='{current_coin}' AND p.from_coin_id = ( SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC LIMIT ( SELECT count(DISTINCT pairs.to_coin_id) FROM pairs WHERE pairs.from_coin_id='{current_coin}');"""
                )
                query = cur.fetchall()

                # Generate message
                last_update = datetime.strptime(query[0][0], "%Y-%m-%d %H:%M:%S.%f")
                query = sorted(query, key=lambda k: k[-1], reverse=True)

                m_list = [
                    f'\nLast update: `{last_update.strftime("%H:%M:%S %d/%m/%Y")}`\n\n*Coin ratios compared to {current_coin}:*\n'.replace(
                        ".", "\."
                    )
                ]
                for coin in query:
                    m_list.append(
                        f"*{coin[1]}*:\n\t\- Price: `{coin[2]}` {bridge}\n\t\- Ratio: `{round(coin[3], 6)}`\n\n".replace(
                            ".", "\."
                        )
                    )

                message = text_4096_cutter(m_list)
                con.close()
            except:
                con.close()
                return [
                    f"❌ Something went wrong, unable to generate ratios at this time\."
                ]
        except:
            message = ["❌ Unable to perform actions on the database\."]
    return message


def check_status():
    logger.info("Check status button pressed.")

    message = "⚠ Binance Trade Bot is not running."
    if find_process():
        message = "✔ Binance Trade Bot is running."
    return message


def trade_history():
    logger.info("Trade history button pressed.")

    db_file_path = f"{settings.ROOT_PATH}data/crypto_trading.db"
    message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
    if os.path.exists(db_file_path):
        try:
            con = sqlite3.connect(db_file_path)
            cur = con.cursor()

            # Get last 10 trades
            try:
                cur.execute(
                    """SELECT alt_coin_id, crypto_coin_id, selling, state, alt_trade_amount, crypto_trade_amount, datetime FROM trade_history ORDER BY datetime DESC LIMIT 10;"""
                )
                query = cur.fetchall()

                m_list = [
                    f"Last **{10 if len(query) > 10 else len(query)}** trades:\n\n"
                ]
                for trade in query:
                    d = datetime.strptime(trade[6], "%Y-%m-%d %H:%M:%S.%f")
                    m = f'`{d.strftime("%H:%M:%S %d/%m/%Y")}`\n*{"Sold" if trade[2] else "Bought"}* `{round(trade[4], 6)}` *{trade[0]}*{f" for `{round(trade[5], 2)}` *{trade[1]}*" if trade[5] is not None else ""}\nStatus: _*{trade[3]}*_\n\n'
                    m_list.append(m.replace(".", "\."))

                message = text_4096_cutter(m_list)
                con.close()
            except:
                con.close()
                return [
                    f"❌ Something went wrong, unable to generate trade history at this time\."
                ]
        except:
            message = ["❌ Unable to perform actions on the database\."]
    return message


def start_bot():
    logger.info("Start bot button pressed.")

    message = "⚠ Binance Trade Bot is already running\."
    if not find_process():
        if os.path.exists(f"{settings.ROOT_PATH}binance_trade_bot/"):
            subprocess.call(
                f"cd {settings.ROOT_PATH} && $(which python3) -m binance_trade_bot &",
                shell=True,
            )
            if not find_process():
                message = "❌ Unable to start Binance Trade Bot\."
            else:
                message = "✔ Binance Trade Bot successfully started\."
        else:
            message = "❌ Unable to find _Binance Trade Bot_ installation in this directory\.\nMake sure the `BTBManagerTelegram.py` file is in the _Binance Trade Bot_ installation folder\."
    return message


def stop_bot(self):
    self.logger.info("Stop bot button pressed.")

    message = "⚠ Binance Trade Bot is not running."
    if find_process():
        self.__find_and_kill_process()
        if not find_process():
            message = "✔ Successfully stopped the bot."
        else:
            message = "❌ Unable to stop Binance Trade Bot.\n\nIf you are running the telegram bot on Windows make sure to run with administrator privileges."
    return message


def read_log():
    logger.info("Read log button pressed.")

    log_file_path = f"{settings.ROOT_PATH}logs/crypto_trading.log"
    message = f"❌ Unable to find log file at `{log_file_path}`.".replace(".", "\.")
    if os.path.exists(log_file_path):
        with open(log_file_path) as f:
            file_content = f.read().replace(".", "\.")[-4000:]
            message = f"Last *4000* characters in log file:\n\n```\n{file_content}\n```"
    return message


def delete_db():
    logger.info("Delete database button pressed.")

    message = "⚠ Please stop Binance Trade Bot before deleting the database file\."
    delete = False
    db_file_path = f"{settings.ROOT_PATH}data/crypto_trading.db"
    if not find_process():
        if os.path.exists(db_file_path):
            message = "Are you sure you want to delete the database file?"
            delete = True
        else:
            message = f"⚠ Unable to find database file at `{db_file_path}`.".replace(
                ".", "\."
            )
    return [message, delete]


def edit_user_cfg():
    logger.info("Edit user configuration button pressed.")

    message = "⚠ Please stop Binance Trade Bot before editing user configuration file\."
    edit = False
    user_cfg_file_path = f"{settings.ROOT_PATH}user.cfg"
    if not find_process():
        if os.path.exists(user_cfg_file_path):
            with open(user_cfg_file_path) as f:
                message = f"Current configuration file is:\n\n```\n{f.read()}\n```\n\n_*Please reply with a message containing the updated configuration*_.\n\nWrite /stop to stop editing and exit without changes.".replace(
                    ".", "\."
                )
                edit = True
        else:
            message = f"❌ Unable to find user configuration file at `{user_cfg_file_path}`.".replace(
                ".", "\."
            )
    return [message, edit]


def edit_coin():
    logger.info("Edit coin list button pressed.")

    message = "⚠ Please stop Binance Trade Bot before editing the coin list\."
    edit = False
    coin_file_path = f"{settings.ROOT_PATH}supported_coin_list"
    if not find_process():
        if os.path.exists(coin_file_path):
            with open(coin_file_path) as f:
                message = f"Current coin list is:\n\n```\n{f.read()}\n```\n\n_*Please reply with a message containing the updated coin list*_.\n\nWrite /stop to stop editing and exit without changes.".replace(
                    ".", "\."
                )
                edit = True
        else:
            message = f"❌ Unable to find coin list file at `{coin_file_path}`.".replace(
                ".", "\."
            )
    return [message, edit]


def export_db(self):
    self.logger.info("Export database button pressed.")

    message = "⚠ Please stop Binance Trade Bot before exporting the database file\."
    db_file_path = f"{settings.ROOT_PATH}data/crypto_trading.db"
    fil = None
    if not find_process():
        if os.path.exists(db_file_path):
            with open(db_file_path, "rb") as db:
                fil = db.read()
            message = "Here is your database file:"
        else:
            message = "❌ Unable to Export the database file\."
    return [message, fil]


def update_tg_bot():
    logger.info("Update Telegram bot button pressed.")

    p = subprocess.Popen(
        ["bash", "-c", "git remote update && git status -uno"],
        stdout=subprocess.PIPE,
    )
    output, _ = p.communicate()
    upd = False
    message = "Your BTB Manager Telegram installation is already up to date\."
    if "Your branch is behind" in str(output):
        message = "An update for BTB Manager Telegram is available\.\nWould you like to update now?"
        upd = True
    return [message, upd]


def update_btb():
    logger.info("Update Binance Trade Bot button pressed.")

    upd = False
    try:
        p = subprocess.Popen(
            [
                "bash",
                "-c",
                "cd ../binance-trade-bot && git remote update && git status -uno",
            ],
            stdout=subprocess.PIPE,
        )
        output, _ = p.communicate()

        message = "Your Binance Trade Bot installation is already up to date\."
        if "Your branch is behind" in str(output):
            message = "An update for Binance Trade Bot is available\.\nWould you like to update now?"
            upd = True
    except:
        message = "Error while trying to fetch Binance Trade Bot version information\."
    return [message, upd]
