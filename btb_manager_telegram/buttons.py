import os
import sqlite3
import subprocess
from configparser import ConfigParser
from datetime import datetime
from dateutil import tz


from btb_manager_telegram import BOUGHT, BUYING, SELLING, SOLD, logger, settings
from btb_manager_telegram.binance_api_utils import get_current_price, get_wallet_balance
from btb_manager_telegram.utils import (
    find_and_kill_binance_trade_bot_process,
    format_float,
    get_binance_trade_bot_process,
    is_btb_bot_update_available,
    is_tg_bot_update_available,
    telegram_text_truncator,
    load_custom_settings,
    convert_custom_currency,
    custom_timezone,
)

try:
    FROM_ZONE = custom_timezone()["from_zone"]
    TO_ZONE = custom_timezone()["to_zone"]
except:
    print("custom_timezone_key_not_set")


def current_value():
    logger.info("Current value button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
    if os.path.exists(db_file_path):
        try:
            con = sqlite3.connect(db_file_path)
            cur = con.cursor()

            # Get current coin symbol, bridge symbol, order state, order size, initial buying price
            try:
                cur.execute(
                    """SELECT alt_coin_id, crypto_coin_id, state, alt_trade_amount, crypto_starting_balance, crypto_trade_amount FROM trade_history ORDER BY datetime DESC LIMIT 1;"""
                )
                (
                    current_coin,
                    bridge,
                    state,
                    alt_amount,
                    order_size,
                    buy_price,
                ) = cur.fetchone()
                if current_coin is None:
                    raise Exception()
                if state == "ORDERED":
                    return [
                        f"A buy order of `{format_float(order_size)}` *{bridge}* is currently placed on coin *{current_coin}*.\n\n"
                        f"_Waiting for buy order to complete_.".replace(".", "\.")
                    ]
            except Exception as e:
                logger.error(
                    f"❌ Unable to fetch current coin from database: {e}", exc_info=True
                )
                con.close()
                return ["❌ Unable to fetch current coin from database\."]

            # Get balance, current coin price in USD, current coin price in BTC
            try:
                cur.execute(
                    f"""SELECT balance, usd_price, btc_price, datetime
                        FROM 'coin_value'
                        WHERE coin_id = '{current_coin}'
                        ORDER BY datetime DESC LIMIT 1;"""
                )
                query = cur.fetchone()

                cur.execute(
                    """SELECT cv.balance, cv.usd_price
                        FROM coin_value as cv
                        WHERE cv.coin_id = (SELECT th.alt_coin_id FROM trade_history as th WHERE th.datetime > DATETIME ('now', '-1 day') AND th.selling = 0 ORDER BY th.datetime ASC LIMIT 1)
                        AND cv.datetime > (SELECT th.datetime FROM trade_history as th WHERE th.datetime > DATETIME ('now', '-1 day') AND th.selling = 0 ORDER BY th.datetime ASC LIMIT 1)
                        ORDER BY cv.datetime ASC LIMIT 1;"""
                )
                query_1_day = cur.fetchone()

                cur.execute(
                    """SELECT cv.balance, cv.usd_price
                        FROM coin_value as cv
                        WHERE cv.coin_id = (SELECT th.alt_coin_id FROM trade_history as th WHERE th.datetime > DATETIME ('now', '-7 day') AND th.selling = 0 ORDER BY th.datetime ASC LIMIT 1)
                        AND cv.datetime > (SELECT th.datetime FROM trade_history as th WHERE th.datetime > DATETIME ('now', '-7 day') AND th.selling = 0 ORDER BY th.datetime ASC LIMIT 1)
                        ORDER BY cv.datetime ASC LIMIT 1;"""
                )
                query_7_day = cur.fetchone()

                if query is None:
                    return [
                        f"❌ No information about *{current_coin}* available in the database\.",
                        "⚠ If you tried using the `Current value` button during a trade please try again after the trade has been completed\.",
                    ]

                balance, usd_price, btc_price, last_update = query
                if balance is None:
                    balance = 0
                if usd_price is None:
                    usd_price = 0
                if btc_price is None:
                    btc_price = 0
                last_update = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S.%f")
                return_rate_1_day, return_rate_7_day = 0, 0
                balance_1_day, usd_price_1_day, balance_7_day, usd_price_7_day = (
                    0,
                    0,
                    0,
                    0,
                )

                if (
                    query_1_day is not None
                    and all(elem is not None for elem in query_1_day)
                    and usd_price != 0
                ):
                    balance_1_day, usd_price_1_day = query_1_day
                    return_rate_1_day = round(
                        (balance * usd_price - balance_1_day * usd_price_1_day)
                        / (balance_1_day * usd_price_1_day)
                        * 100,
                        2,
                    )

                if (
                    query_7_day is not None
                    and all(elem is not None for elem in query_7_day)
                    and usd_price != 0
                ):
                    balance_7_day, usd_price_7_day = query_7_day
                    return_rate_7_day = round(
                        (balance * usd_price - balance_7_day * usd_price_7_day)
                        / (balance_7_day * usd_price_7_day)
                        * 100,
                        2,
                    )
            except Exception as e:
                logger.error(
                    f"❌ Unable to fetch current coin information from database: {e}",
                    exc_info=True,
                )
                con.close()
                return [
                    "❌ Unable to fetch current coin information from database\.",
                    "⚠ If you tried using the `Current value` button during a trade please try again after the trade has been completed\.",
                ]

            # Generate message
            try:
                m_list = [
                    f"\nLast update: `{last_update.replace(tzinfo=FROM_ZONE).astimezone(TO_ZONE).strftime('%H:%M:%S %d/%m/%Y')}`\n\n",
                    f"*Current coin {current_coin}:*\n",
                    f"\t\- Balance: `{format_float(balance)}` *{current_coin}*\n",
                    f"\t\- Exchange rate purchased: `{format_float(buy_price / alt_amount)}` *{bridge}*/*{current_coin}* \n",
                    f"\t\- Exchange rate now: `{format_float(usd_price)}` *USD*/*{current_coin}*\n",
                    f"\t\- Change in value: `{round((balance * usd_price - buy_price) / buy_price * 100, 2)}` *%*\n",
                    f"\t\- Value in *USD*: `{round(balance * usd_price, 2)}` *USD*\n",
                    f"\t\- Value in *BTC*: `{format_float(balance * btc_price)}` *BTC*\n\n",
                    f"_Bought for_ `{round(buy_price, 2)}` *{bridge}*\n",
                    f"_*1 day* value change USD_: `{return_rate_1_day}` *%*\n",
                    f"_*7 days* value change USD_: `{return_rate_7_day}` *%*\n\n",
                ]
                if load_custom_settings()["Custom_Currency_Enabled"]:
                    if convert_custom_currency() != False:
                        custom_currency_data = convert_custom_currency()
                        m_list.insert(
                            7,
                            f"\t\- Value in *{custom_currency_data['Custom_Currency']}*: `{round(custom_currency_data['Converted_Rate'] * usd_price * balance, 2)}` *{custom_currency_data['Custom_Currency']}*\n",
                        )
                    else:
                        m_list.insert(
                            7,
                            f"\t\- *Forex Error*\n",
                        )

                message = telegram_text_truncator(m_list)
                con.close()

            except Exception as e:
                logger.error(
                    f"❌ Something went wrong, unable to generate value at this time: {e}",
                    exc_info=True,
                )
                con.close()
                return [
                    "❌ Something went wrong, unable to generate value at this time\."
                ]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = ["❌ Unable to perform actions on the database\."]
    return message


def binanace_wallet_value():
    wallet_data = get_wallet_balance()
    ts = wallet_data["timestamp"]
    if load_custom_settings()["Custom_Currency_Enabled"]:
        if convert_custom_currency() != False:
            custom_currency_data = convert_custom_currency()
    else:
        custom_currency_data = {"Custom_Currency": "USD", "Converted_Rate": 1}
    m_list = [
        f"\nLast update: `{str(datetime.fromtimestamp(ts).strftime('%H:%M:%S %d/%m/%Y'))}`\n\n",
        f"*Binance Wallet:*\n",
        f"\t\- Estimated Balance: `{wallet_data['walletInusd'] * custom_currency_data['Converted_Rate']:.2f}` *{custom_currency_data['Custom_Currency']}*\n\n",
    ]

    for coin in wallet_data["individualCoins"]:
        m_list.append(
            f"\t\- {coin['asset']}: `{coin['totalInUSD'] * custom_currency_data['Converted_Rate']:.2f}` *{custom_currency_data['Custom_Currency']}*\n"
        )
    message = telegram_text_truncator(m_list)

    return message


def check_progress():
    logger.info("Progress button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
    if os.path.exists(db_file_path):
        try:
            con = sqlite3.connect(db_file_path)
            cur = con.cursor()

            # Get progress information
            try:
                cur.execute(
                    """SELECT th1.alt_coin_id AS coin, th1.alt_trade_amount AS amount, th1.crypto_trade_amount AS priceInUSD,(th1.alt_trade_amount - ( SELECT th2.alt_trade_amount FROM trade_history th2 WHERE th2.state = 'COMPLETE' AND th2.alt_coin_id = th1.alt_coin_id AND th1.datetime > th2.datetime AND th2.selling = 0 ORDER BY th2.datetime DESC LIMIT 1)) AS change, (SELECT th2.datetime FROM trade_history th2 WHERE th2.state = 'COMPLETE' AND th2.alt_coin_id = th1.alt_coin_id AND th1.datetime > th2.datetime AND th2.selling = 0 ORDER BY th2.datetime DESC LIMIT 1) AS pre_last_trade_date, datetime FROM trade_history th1 WHERE th1.state = 'COMPLETE' AND th1.selling = 0 ORDER BY th1.datetime DESC LIMIT 15"""
                )
                query = cur.fetchall()

                # Generate message
                m_list = ["Current coin amount progress:\n\n"]
                if load_custom_settings()["Custom_Currency_Enabled"]:
                    if convert_custom_currency() != False:
                        custom_currency_data = convert_custom_currency()
                for coin in query:
                    last_trade_date = datetime.strptime(coin[5], "%Y-%m-%d %H:%M:%S.%f")
                    if coin[4] is None:
                        pre_last_trade_date = datetime.strptime(
                            coin[5], "%Y-%m-%d %H:%M:%S.%f"
                        )
                    else:
                        pre_last_trade_date = datetime.strptime(
                            coin[4], "%Y-%m-%d %H:%M:%S.%f"
                        )
                    time_passed = last_trade_date - pre_last_trade_date
                    sub_list = [
                        f"*{coin[0]}*\n",
                        f"\t\- Amount: `{format_float(coin[1])}` *{coin[0]}*\n",
                        f"\t\- Price: `{round(coin[2], 2)}` *USD*\n",
                        f"\t\- Change: {f'`{format_float(coin[3])}` *{coin[0]}* `{round(coin[3] / (coin[1] - coin[3]) * 100, 2)}` *%* in {time_passed.days} days, {time_passed.seconds // 3600} hours' if coin[3] is not None else f'`{coin[3]}`'}\n",
                        f"\t\- Trade datetime: `{last_trade_date.replace(tzinfo=FROM_ZONE).astimezone(TO_ZONE).strftime('%H:%M:%S %d/%m/%Y')}`\n\n".replace(
                            ".", "\."
                        ),
                    ]
                    if load_custom_settings()["Custom_Currency_Enabled"] == True:
                        sub_list.insert(
                            3,
                            f"\t\- Price: `{round(custom_currency_data['Converted_Rate'] * coin[2], 2)}` *{custom_currency_data['Custom_Currency']}*\n",
                        )
                    else:
                        sub_list.insert(
                            3,
                            f"\t\- *Forex Error*\n",
                        )
                    m_list.append(sub_list)
                flat_m_list = ["".join(x) for x in m_list]
                message = telegram_text_truncator(flat_m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Unable to fetch progress information from database: {e}",
                    exc_info=True,
                )
                con.close()
                return ["❌ Unable to fetch progress information from database\."]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = ["❌ Unable to perform actions on the database\."]
    return message


def current_ratios():
    logger.info("Current ratios button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
    if os.path.exists(db_file_path):
        try:
            # Get bridge currency symbol
            with open(user_cfg_file_path) as cfg:
                config = ConfigParser()
                config.read_file(cfg)
                bridge = config.get("binance_user_config", "bridge")
                scout_multiplier = config.get("binance_user_config", "scout_multiplier")

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
            except Exception as e:
                logger.error(
                    f"❌ Unable to fetch current coin from database: {e}", exc_info=True
                )
                con.close()
                return ["❌ Unable to fetch current coin from database\."]

            # Get prices and ratios of all alt coins
            try:
                cur.execute(
                    f"""SELECT sh.datetime, p.to_coin_id, sh.other_coin_price, ( ( ( current_coin_price / other_coin_price ) - 0.001 * '{scout_multiplier}' * ( current_coin_price / other_coin_price ) ) - sh.target_ratio ) AS 'ratio_dict' FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id='{current_coin}' AND p.from_coin_id = ( SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC LIMIT ( SELECT count(DISTINCT pairs.to_coin_id) FROM pairs JOIN coins ON coins.symbol = pairs.to_coin_id WHERE coins.enabled = 1 AND pairs.from_coin_id='{current_coin}');"""
                )
                query = cur.fetchall()

                # Generate message
                last_update = datetime.strptime(query[0][0], "%Y-%m-%d %H:%M:%S.%f")
                query = sorted(query, key=lambda k: k[-1], reverse=True)

                m_list = [
                    f"\nLast update: `{last_update.replace(tzinfo=FROM_ZONE).astimezone(TO_ZONE).strftime('%H:%M:%S %d/%m/%Y')}`\n\n"
                    f"*Coin ratios compared to {current_coin} in decreasing order:*\n".replace(
                        ".", "\."
                    )
                ]
                for coin in query:
                    m_list.append(
                        f"*{coin[1]}*:\n"
                        f"\t\- Price: `{coin[2]}` {bridge}\n"
                        f"\t\- Ratio: `{format_float(coin[3])}`\n\n".replace(".", "\.")
                    )

                message = telegram_text_truncator(m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Something went wrong, unable to generate ratios at this time: {e}",
                    exc_info=True,
                )
                con.close()
                return [
                    "❌ Something went wrong, unable to generate ratios at this time\.",
                    "⚠ Please make sure logging for _Binance Trade Bot_ is enabled\.",
                ]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = ["❌ Unable to perform actions on the database\."]
    return message


def next_coin():
    logger.info("Next coin button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
    if os.path.exists(db_file_path):
        try:
            # Get bridge currency symbol
            with open(user_cfg_file_path) as cfg:
                config = ConfigParser()
                config.read_file(cfg)
                bridge = config.get("binance_user_config", "bridge")
                scout_multiplier = config.get("binance_user_config", "scout_multiplier")

            con = sqlite3.connect(db_file_path)
            cur = con.cursor()

            # Get prices and percentages for a jump to the next coin
            try:
                cur.execute(
                    f"""SELECT p.to_coin_id as other_coin, sh.other_coin_price, (current_coin_price - 0.001 * '{scout_multiplier}' * current_coin_price) / sh.target_ratio AS 'price_needs_to_drop_to', ((current_coin_price - 0.001 * '{scout_multiplier}' * current_coin_price) / sh.target_ratio) / sh.other_coin_price as 'percentage' FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id = (SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC, percentage DESC LIMIT (SELECT count(DISTINCT pairs.to_coin_id) FROM pairs JOIN coins ON coins.symbol = pairs.to_coin_id WHERE coins.enabled = 1 AND pairs.from_coin_id=(SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1));"""
                )
                query = cur.fetchall()

                m_list = []
                for coin in query:
                    percentage = round(coin[3] * 100, 2)
                    m_list.append(
                        f"*{coin[0]} \(`{format_float(percentage)}`%\)*\n"
                        f"\t\- Current Price: `{format_float(round(coin[1], 8))}` {bridge}\n"
                        f"\t\- Target Price: `{format_float(round(coin[2], 8))}` {bridge}\n\n".replace(
                            ".", "\."
                        )
                    )

                message = telegram_text_truncator(m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Something went wrong, unable to generate next coin at this time: {e}",
                    exc_info=True,
                )
                con.close()
                return [
                    "❌ Something went wrong, unable to generate next coin at this time\.",
                    "⚠ Please make sure logging for _Binance Trade Bot_ is enabled\.",
                ]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = ["❌ Unable to perform actions on the database\."]
    return message


def check_status():
    logger.info("Check status button pressed.")

    message = "⚠ Binance Trade Bot is not running."
    if get_binance_trade_bot_process():
        message = "✔ Binance Trade Bot is running."
    return message


def trade_history():
    logger.info("Trade history button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
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
                    if trade[4] is None:
                        continue
                    date = datetime.strptime(trade[6], "%Y-%m-%d %H:%M:%S.%f")
                    date = date.replace(tzinfo=FROM_ZONE)
                    date = date.astimezone(TO_ZONE)
                    m_list.append(
                        f"`{date.strftime('%H:%M:%S %d/%m/%Y')}`\n"
                        f"*{'Sold' if trade[2] else 'Bought'}* `{format_float(trade[4])}` *{trade[0]}*{f' for `{format_float(trade[5])}` *{trade[1]}*' if trade[5] is not None else ''}\n"
                        f"Status: _*{trade[3]}*_\n\n".replace(".", "\.")
                    )

                message = telegram_text_truncator(m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Something went wrong, unable to generate trade history at this time: {e}",
                    exc_info=True,
                )
                con.close()
                return [
                    "❌ Something went wrong, unable to generate trade history at this time\."
                ]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = ["❌ Unable to perform actions on the database\."]
    return message


def start_bot():
    logger.info("Start bot button pressed.")

    message = "⚠ Binance Trade Bot is already running\."
    if not get_binance_trade_bot_process():
        if os.path.isfile(settings.PYTHON_PATH):
            if os.path.exists(os.path.join(settings.ROOT_PATH, "binance_trade_bot/")):
                subprocess.call(
                    f"cd {settings.ROOT_PATH} && {settings.PYTHON_PATH} -m binance_trade_bot &",
                    shell=True,
                )
                if get_binance_trade_bot_process():
                    message = "✔ Binance Trade Bot successfully started\."
                else:
                    message = "❌ Unable to start Binance Trade Bot\."
            else:
                message = (
                    f"❌ Unable to find _Binance Trade Bot_ installation at `{settings.ROOT_PATH}`\.\n"
                    f"Make sure the `binance-trade-bot` and `BTB-manager-telegram` are in the same parent directory\."
                )
        else:
            message = f"❌ Unable to find python binary at `{settings.PYTHON_PATH}`\.\n"
    return message


def stop_bot():
    logger.info("Stop bot button pressed.")

    message = "⚠ Binance Trade Bot is not running."
    if get_binance_trade_bot_process():
        find_and_kill_binance_trade_bot_process()
        if not get_binance_trade_bot_process():
            message = "✔ Successfully stopped the bot."
        else:
            message = (
                "❌ Unable to stop Binance Trade Bot.\n\n"
                "If you are running the telegram bot on Windows make sure to run with administrator privileges."
            )
    return message


def read_log():
    logger.info("Read log button pressed.")

    log_file_path = os.path.join(settings.ROOT_PATH, "logs/crypto_trading.log")
    message = f"❌ Unable to find log file at `{log_file_path}`.".replace(".", "\.")
    if os.path.exists(log_file_path):
        with open(log_file_path) as f:
            file_content = f.read().replace(".", "\.")[-4000:]
            message = (
                f"Last *4000* characters in log file:\n\n"
                f"```\n"
                f"{file_content}\n"
                f"```"
            )
    return message


def delete_db():
    logger.info("Delete database button pressed.")

    message = "⚠ Please stop Binance Trade Bot before deleting the database file\."
    delete = False
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    if not get_binance_trade_bot_process():
        if os.path.exists(db_file_path):
            message = (
                "Are you sure you want to delete the database file and clear the logs?"
            )
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
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    if not get_binance_trade_bot_process():
        if os.path.exists(user_cfg_file_path):
            with open(user_cfg_file_path) as f:
                message = (
                    f"Current configuration file is:\n\n"
                    f"```\n"
                    f"{f.read()}\n"
                    f"```\n\n"
                    f"_*Please reply with a message containing the updated configuration*_.\n\n"
                    f"Write /stop to stop editing and exit without changes.".replace(
                        ".", "\."
                    )
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
    coin_file_path = os.path.join(settings.ROOT_PATH, "supported_coin_list")
    if not get_binance_trade_bot_process():
        if os.path.exists(coin_file_path):
            with open(coin_file_path) as f:
                message = (
                    f"Current coin list is:\n\n"
                    f"```\n{f.read()}\n```\n\n"
                    f"_*Please reply with a message containing the updated coin list*_.\n\n"
                    f"Write /stop to stop editing and exit without changes.".replace(
                        ".", "\."
                    )
                )
                edit = True
        else:
            message = f"❌ Unable to find coin list file at `{coin_file_path}`.".replace(
                ".", "\."
            )
    return [message, edit]


def export_db():
    logger.info("Export database button pressed.")

    message = "⚠ Please stop Binance Trade Bot before exporting the database file\."
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    fil = None
    if not get_binance_trade_bot_process():
        if os.path.exists(db_file_path):
            with open(db_file_path, "rb") as db:
                fil = db.read()
            message = "Here is your database file:"
        else:
            message = "❌ Unable to Export the database file\."
    return [message, fil]


def update_tg_bot():
    logger.info("⬆ Update Telegram Bot button pressed.")

    message = "Your BTB Manager Telegram installation is already up to date\."
    upd = False
    to_update = is_tg_bot_update_available()
    if to_update is not None:
        if to_update:
            message = (
                "An update for BTB Manager Telegram is available\.\n"
                "Would you like to update now?"
            )
            upd = True
    else:
        message = (
            "Error while trying to fetch BTB Manager Telegram version information\."
        )
    return [message, upd]


def update_btb():
    logger.info("⬆ Update Binance Trade Bot button pressed.")

    message = "Your Binance Trade Bot installation is already up to date\."
    upd = False
    to_update = is_btb_bot_update_available()
    if to_update is not None:
        if to_update:
            upd = True
            message = (
                "An update for Binance Trade Bot is available\.\n"
                "Would you like to update now?"
            )
    else:
        message = "Error while trying to fetch Binance Trade Bot version information\."
    return [message, upd]


def panic_btn():
    logger.info("🚨 Panic Button button pressed.")

    # Check if open orders / not in usd
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    if not os.path.exists(db_file_path):
        return ["ERROR: Database file not found\.", -1]

    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    if not os.path.exists(user_cfg_file_path):
        return ["ERROR: `user.cfg` file not found\.", -1]

    try:
        con = sqlite3.connect(db_file_path)
        cur = con.cursor()

        # Get last trade
        try:
            cur.execute(
                """SELECT alt_coin_id, crypto_coin_id, selling, state, alt_trade_amount, crypto_trade_amount FROM trade_history ORDER BY datetime DESC LIMIT 1;"""
            )
            (
                alt_coin_id,
                crypto_coin_id,
                selling,
                state,
                alt_trade_amount,
                crypto_trade_amount,
            ) = cur.fetchone()

            if not selling:
                price_old = crypto_trade_amount / alt_trade_amount
                price_now = get_current_price(alt_coin_id, crypto_coin_id)
                if state == "COMPLETE":
                    return [
                        f"You are currently holding `{round(alt_trade_amount, 6)}` *{alt_coin_id}* bought for `{round(crypto_trade_amount, 2)}` *{crypto_coin_id}*.\n\n"
                        f"Exchange rate when bought:\n"
                        f"`{round(price_old, 4)}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"Current exchange rate:\n"
                        f"`{round(price_now, 4)}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"Current value:\n"
                        f"`{round(price_now * alt_trade_amount, 4)}` *{crypto_coin_id}*\n\n"
                        f"Change:\n"
                        f"`{round((price_now - price_old) / price_old * 100, 2)}` *%*\n\n"
                        f"Would you like to stop _Binance Trade Bot_ and sell at market price?".replace(
                            ".", "\."
                        ),
                        BOUGHT,
                    ]
                else:
                    return [
                        f"You have an open buy order of `{alt_trade_amount}` *{alt_coin_id}* for `{crypto_trade_amount}` *{crypto_coin_id}*.\n\n"
                        f"Limit buy at price:\n"
                        f"`{round(price_old, 4)}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"Current exchange rate:\n"
                        f"`{round(price_now, 4)}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"Change:\n"
                        f"`{round((price_now - price_old) / price_old * 100, 2)}` *%*\n\n"
                        f"Would you like to stop _Binance Trade Bot_ and cancel the open order?".replace(
                            ".", "\."
                        ),
                        BUYING,
                    ]
            else:
                if state == "COMPLETE":
                    return [
                        f"Your balance is already in *{crypto_coin_id}*.\n\n"
                        f"Would you like to stop _Binance Trade Bot_?".replace(
                            ".", "\."
                        ),
                        SOLD,
                    ]
                else:
                    price_old = crypto_trade_amount / alt_trade_amount
                    price_now = get_current_price(alt_coin_id, crypto_coin_id)
                    return [
                        f"You have an open sell order of `{alt_trade_amount}` *{alt_coin_id}* for `{crypto_trade_amount}` *{crypto_coin_id}*.\n\n"
                        f"Limit sell at price:\n"
                        f"`{round(price_old, 4)}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"Current exchange rate:\n"
                        f"`{round(price_now, 4)}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"Change:\n"
                        f"`{round((price_now - price_old) / price_old * 100, 2)}` *%*\n\n"
                        f"Would you like to stop _Binance Trade Bot_ and cancel the open order?".replace(
                            ".", "\."
                        ),
                        SELLING,
                    ]

            con.close()
        except Exception as e:
            con.close()
            logger.error(
                f"❌ Something went wrong, the panic button is not working at this time: {e}",
                exc_info=True,
            )
            return [
                "❌ Something went wrong, the panic button is not working at this time\.",
                -1,
            ]
    except Exception as e:
        logger.error(f"❌ Unable to perform actions on the database: {e}", exc_info=True)
        return ["❌ Unable to perform actions on the database\.", -1]
