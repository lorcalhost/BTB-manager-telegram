import os
import sqlite3
import subprocess
from configparser import ConfigParser
from datetime import datetime

import i18n
from btb_manager_telegram import BOUGHT, BUYING, SELLING, SOLD, logger, settings
from btb_manager_telegram.binance_api_utils import get_current_price
from btb_manager_telegram.utils import (
    find_and_kill_binance_trade_bot_process,
    format_float,
    get_binance_trade_bot_process,
    is_btb_bot_update_available,
    is_tg_bot_update_available,
    telegram_text_truncator,
    escape_tg
)


def current_value():
    logger.info("Current value button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    message = [i18n.t("database_not_found", path=escape_tg(db_file_path))]
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
                        f"{i18n.t('order_placed', order_size=format_float(order_size), bridge=bridge, current_coin=current_coin)}\n\n"
                        f"{i18n.t('wait_for_order')}"
                    ]
            except Exception as e:
                logger.error(
                    f"❌ Unable to fetch current coin from database: {e}", exc_info=True
                )
                con.close()
                return [i18n.t("fetch_coin_from_db_error")]

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
                        i18n.t("no_information", current_coin=current_coin),
                        i18n.t("no_current_value_during_trade"),
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
                    i18n.t("fetch_coin_from_db_error"),
                    i18n.t("no_current_value_during_trade"),
                ]

            # Generate message
            try:
                m_list = [
                    f"\n{i18n.t('last_update', update=last_update.strftime('%H:%M:%S %d/%m/%Y'))}\n\n",
                    f"{i18n.t('current_coin', coin=current_coin)}\n",
                    f"\t{i18n.t('balance', balance=format_float(balance), coin=current_coin)}\n",
                    f"\t{i18n.t('exchange_rate_purchased', rate=format_float(buy_price / alt_amount), bridge=bridge, coin=current_coin)}\n",
                    f"\t{i18n.t('exchange_rate_now', rate=format_float(usd_price), coin=current_coin)}\n",
                    f"\t{i18n.t('value_change', change=round((balance * usd_price - buy_price) / buy_price * 100, 2))}\n",
                    f"\t{i18n.t('value_usd', value=round(balance * usd_price, 2))}\n",
                    f"\t{i18n.t('value_btc', value=round(balance * btc_price))}\n\n",
                    f"{i18n.t('bought_for', value=round(buy_price, 2), coin=bridge)}\n"
                    f"{i18n.t('one_day_change_btc', value=return_rate_1_day)}\n",
                    f"{i18n.t('seven_day_change_btc', value=return_rate_7_day)}\n",
                ]
                message = telegram_text_truncator(m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Something went wrong, unable to generate value at this time: {e}",
                    exc_info=True,
                )
                con.close()
                return [i18n.t("error_generating_value")]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("db_action_error")]
    return message


def check_progress():
    logger.info("Progress button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    message = [i18n.t("database_not_found", path=escape_tg(db_file_path))]
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
                m_list = [f"{i18n.t('coin_progress')}\n\n"]
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
                    last_trade_date = last_trade_date.strftime("%H:%M:%S %d/%m/%Y")
                    change = (
                        i18n.t(
                            "change_over_days",
                            amount=format_float(coin[3]),
                            coin=coin[0],
                            percent=round(coin[3] / (coin[1] - coin[3]) * 100, 2),
                            days=time_passed.days,
                            hours=time_passed.seconds // 3600,
                        )
                        if coin[3] is not None
                        else coin[3]
                    )
                    m_list.append(
                        f"*{coin[0]}*\n"
                        f"\t{i18n.t('amount', amount=format_float(coin[1]), coin=coin[0])}\n"
                        f"\t{i18n.t('price', amount=round(coin[2], 2))}\n"
                        f"\t{change}\n"
                        f"\t{i18n.t('trade_datetime', date=escape_tg(last_trade_date))}\n\n"
                    )

                message = telegram_text_truncator(m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Unable to fetch progress information from database: {e}",
                    exc_info=True,
                )
                con.close()
                return [i18n.t("progress_fetch_error")]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("db_action_error")]
    return message


def current_ratios():
    logger.info("Current ratios button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    message = [i18n.t("database_not_found", path=escape_tg(db_file_path))]
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
                return [i18n.t("fetch_coin_from_db_error")]

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
                    f"\n{i18n.t('last_update', update=last_update.strftime('%H:%M:%S %d/%m/%Y'))}\n\n"
                    f"{i18n.t('compared_ratios', coin=escape_tg(current_coin))}\n"
                ]
                for coin in query:
                    m_list.append(
                        f"*{coin[1]}*:\n"
                        f"\t{i18n.t('bridge_value', value=coin[2], bridge=bridge)}\n"
                        f"\t{i18n.t('ratio', ratio=escape_tg(format_float(coin[3])))}\n\n"
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
                    i18n.t("ratio_gen_error"),
                    i18n.t("logging_enabled_error"),
                ]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("db_action_error")]
    return message


def next_coin():
    logger.info("Next coin button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    message = [f"{i18n.t('database_not_found', path=db_file_path)}"]
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
                query = sorted(query, key=lambda x: x[3], reverse=True)
                for coin in query:
                    percentage = round(coin[3] * 100, 2)
                    m_list.append(
                        f"*{coin[0]} \(`{format_float(percentage)}`%\)*\n"
                        f"\t{i18n.t('current_price', price=format_float(round(coin[1], 8)), coin=bridge)}\n"
                        f"\t{i18n.t('target_price', price=format_float(round(coin[2], 8)), coin=bridge)}\n\n"
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
                    i18n.t("next_coin_error"),
                    i18n.t("logging_enabled_error"),
                ]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("db_action_error")]
    return message


def check_status():
    logger.info("Check status button pressed.")

    message = i18n.t("bot_not_running")
    if get_binance_trade_bot_process():
        message = i18n.t("bot_running")
    return message


def trade_history():
    logger.info("Trade history button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    message = [i18n.t("database_not_found", path=escape_tg(db_file_path))]
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
                    f"{i18n.t('last_x_trades', trades=10 if len(query) > 10 else len(query))}\n\n"
                ]
                for trade in query:
                    if trade[4] is None:
                        continue
                    date = datetime.strptime(trade[6], "%Y-%m-%d %H:%M:%S.%f")
                    if trade[5] is not None:
                        trade_details = i18n.t(
                            "sold_bought",
                            sold_trade="Sold" if trade[2] else "Bought",
                            amount1=format_float(trade[4]),
                            coin1=trade[0],
                            amount2=format_float(trade[5]),
                            coin2=trade[1],
                        )
                    else:
                        trade_details = ""

                    m_list.append(
                        f"`{date.strftime('%H:%M:%S %d/%m/%Y')}`\n"
                        f"{trade_details}\n"
                        f"{i18n.t('trade_status', status=trade[3])}\n\n"
                    )

                message = telegram_text_truncator(m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Something went wrong, unable to generate trade history at this time: {e}",
                    exc_info=True,
                )
                con.close()
                return [i18n.t("trade_history_error")]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("db_action_error")]
    return message


def start_bot():
    logger.info("Start bot button pressed.")

    message = i18n.t("bot_already_running")
    if not get_binance_trade_bot_process():
        if os.path.isfile(settings.PYTHON_PATH):
            if os.path.exists(os.path.join(settings.ROOT_PATH, "binance_trade_bot/")):
                subprocess.call(
                    f"cd {settings.ROOT_PATH} && {settings.PYTHON_PATH} -m binance_trade_bot &",
                    shell=True,
                )
                if get_binance_trade_bot_process():
                    message = i18n.t("bot_started")
                else:
                    message = i18n.t("bot_start_error")
            else:
                message = (
                    f"{i18n.t('installation_path_error', path=settings.ROOT_PATH)}\n"
                    f"{i18n.t('directory_hint')}"
                )
        else:
            message = f"{i18n.t('python_lib_error', path=settings.PYTHON_PATH)}\n"
    return message


def stop_bot():
    logger.info("Stop bot button pressed.")

    message = i18n.t("bot_not_running")
    if get_binance_trade_bot_process():
        find_and_kill_binance_trade_bot_process()
        if not get_binance_trade_bot_process():
            message = i18n.t("stopped_bot")
        else:
            message = f"{i18n.t('stop_error')}\n\n" f"{i18n.t('windows_hint')}"
    return message


def read_log():
    logger.info("Read log button pressed.")

    log_file_path = os.path.join(settings.ROOT_PATH, "logs/crypto_trading.log")
    message = f"{i18n.t('log_file_error', path=escape_tg(log_file_path))}"
    if os.path.exists(log_file_path):
        with open(log_file_path) as f:
            file_content = escape_tg(f.read())[-4000:]
            message = (
                f"{i18n.t('last_4000_characters')}\n\n"
                f"```\n"
                f"{file_content}\n"
                f"```"
            )
    return message


def delete_db():
    logger.info("Delete database button pressed.")

    message = i18n.t("stop_bot_before_delete")
    delete = False
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    if not get_binance_trade_bot_process():
        if os.path.exists(db_file_path):
            message = i18n.t("sure_delete")
            delete = True
        else:
            message = f"{i18n.t('database_not_found', path=escape_tg(db_file_path))}"
    print(message)
    return [message, delete]


def edit_user_cfg():
    logger.info("Edit user configuration button pressed.")

    message = i18n.t("stop_bot_before_edit_config")
    edit = False
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    if not get_binance_trade_bot_process():
        if os.path.exists(user_cfg_file_path):
            with open(user_cfg_file_path) as f:
                message = (
                    f"{i18n.t('config_file_is')}\n\n"
                    f"```\n"
                    f"{escape_tg(f.read())}\n"
                    f"```\n\n"
                    f"{i18n.t('reply_config')}\n\n"
                    f"{i18n.t('stop_to_stop')}"
                )
                edit = True
        else:
            message = f"{i18n.t('config_file_error', path=escape_tg(user_cfg_file_path))}"
    return [message, edit]


def edit_coin():
    logger.info("Edit coin list button pressed.")

    message = i18n.t("stop_bot_before_edit_coin_list")
    edit = False
    coin_file_path = os.path.join(settings.ROOT_PATH, "supported_coin_list")
    if not get_binance_trade_bot_process():
        if os.path.exists(coin_file_path):
            with open(coin_file_path) as f:
                message = (
                    f"{i18n.t('coin_list_is')}\n\n"
                    f"```\n{escape_tg(f.read())}\n```\n\n"
                    f"{i18n.t('reply_coin_list')}\n\n"
                    f"{i18n.t('stop_to_stop')}"
                )
                edit = True
        else:
            message = f"{i18n.t('coin_list_error', path=escape_tg(coin_file_path))}"
    return [message, edit]


def export_db():
    logger.info("Export database button pressed.")

    message = i18n.t("stop_bot_before_export")
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    file = None
    if not get_binance_trade_bot_process():
        if os.path.exists(db_file_path):
            with open(db_file_path, "rb") as db:
                file = db.read()
            message = i18n.t("file_msg")
        else:
            message = i18n.t("database_export_error")
    return [message, file]


def update_tg_bot():
    logger.info("⬆ Update Telegram Bot button pressed.")

    message = i18n.t("tg_bot_up_to_date")
    upd = False
    to_update = is_tg_bot_update_available()
    if to_update is not None:
        if to_update:
            message = f"{i18n.t('tg_bot_update_availabe')}\n" f"{i18n.t('update_now')}"
            upd = True
    else:
        message = i18n.t("tg_bot_update_error")
    return [message, upd]


def update_btb():
    logger.info("⬆ Update Binance Trade Bot button pressed.")

    message = i18n.t("btb_up_to_date")
    upd = False
    to_update = is_btb_bot_update_available()
    if to_update is not None:
        if to_update:
            upd = True
            message = f"{i18n.t('btb_update_availabe')}\n" f"{i18n.t('update_now')}"
    else:
        message = i18n.t("btb_update_error")
    return [message, upd]


def panic_btn():
    logger.info("🚨 Panic Button button pressed.")

    # Check if open orders / not in usd
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    if not os.path.exists(db_file_path):
        return [i18n.t("panic_db_error"), -1]

    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    if not os.path.exists(user_cfg_file_path):
        return [i18n.t("panic_config_error"), -1]

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
                    con.close()
                    return [
                        f"{i18n.t('holding', amount1=format_float(round(alt_trade_amount, 6)), coin1=alt_coin_id, amount2=format_float(round(crypto_trade_amount, 2)), coin2=crypto_coin_id)}\n\n "
                        f"{i18n.t('rate_when_bought')}\n"
                        f"`{format_float(round(price_old, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('current_rate')}\n"
                        f"`{format_float(round(price_now, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('current_value')}\n"
                        f"`{format_float(round(price_now * alt_trade_amount, 4))}` *{crypto_coin_id}*\n\n"
                        f"{i18n.t('change')}\n"
                        f"`{format_float(round((price_now - price_old) / price_old * 100, 2))}` *%*\n\n"
                        f"{i18n.t('stop_and_sell')}",
                        BOUGHT,
                    ]
                else:
                    con.close()
                    return [
                        f"{i18n.t('open_buy_order', amount1=format_float(alt_trade_amount), coin1=alt_coin_id, amount2=format_float(crypto_trade_amount), coin2=crypto_coin_id)}\n\n"
                        f"{i18n.t('limit_buy_price')}\n"
                        f"`{format_float(round(price_old, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('current_rate')}\n"
                        f"`{format_float(round(price_now, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('change')}\n"
                        f"`{format_float(round((price_now - price_old) / price_old * 100, 2))}` *%*\n\n"
                        f"{i18n.t('stop_and_cancel')}",
                        BUYING,
                    ]
            else:
                if state == "COMPLETE":
                    con.close()
                    return [
                        f"{i18n.t('order_already_complete', coin=crypto_coin_id)}\n\n"
                        f"{i18n.t('ask_stop_bot')}",
                        SOLD,
                    ]
                else:
                    price_old = crypto_trade_amount / alt_trade_amount
                    price_now = get_current_price(alt_coin_id, crypto_coin_id)
                    con.close()
                    return [
                        f"{i18n.t('open_sell_order', amount1=format_float(alt_trade_amount), coin1=alt_coin_id, amount2=format_float(crypto_trade_amount), coin2=crypto_coin_id)}\n\n"
                        f"{i18n.t('limit_sell_price')}\n"
                        f"`{format_float(round(price_old, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('current_rate')}\n"
                        f"`{format_float(round(price_now, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('change')}\n"
                        f"`{format_float(round((price_now - price_old) / price_old * 100, 2))}` *%*\n\n"
                        f"{i18n.t('stop_and_cancel')}",
                        SELLING,
                    ]

        except Exception as e:
            con.close()
            logger.error(
                f"❌ Something went wrong, the panic button is not working at this time: {e}",
                exc_info=True,
            )
            return [
                i18n.t("panic_btn_error"),
                -1,
            ]
    except Exception as e:
        logger.error(f"❌ Unable to perform actions on the database: {e}", exc_info=True)
        return [i18n.t("db_action_error"), -1]
