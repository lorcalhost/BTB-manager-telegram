import os
import sqlite3
import subprocess
import time
from configparser import ConfigParser
from datetime import datetime, timedelta

import i18n
from btb_manager_telegram import BOUGHT, BUYING, SELLING, SOLD, logger, settings
from btb_manager_telegram.binance_api_utils import get_current_price
from btb_manager_telegram.report import get_previous_reports
from btb_manager_telegram.table import float_strip, tabularize
from btb_manager_telegram.utils import (
    find_and_kill_binance_trade_bot_process,
    format_float,
    get_binance_trade_bot_process,
    is_btb_bot_update_available,
    is_tg_bot_update_available,
    setup_coin_list,
    telegram_text_truncator,
)


def current_value():
    logger.info("Current value button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    message = [i18n.t("database_not_found", path=db_file_path)]
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
                        f"{i18n.t('value.order_placed', order_size=order_size, bridge=bridge, current_coin=current_coin)}\n\n"
                        f"{i18n.t('value.wait_for_order')}"
                    ]
            except Exception as e:
                logger.error(
                    f"❌ Unable to fetch current coin from database: {e}", exc_info=True
                )
                con.close()
                return [i18n.t("value.db_error")]

            # Get balance, current coin price in USD, current coin price in BTC
            try:
                cur.execute(
                    f"""SELECT balance, usd_price, btc_price, datetime
                        FROM 'coin_value'
                        WHERE coin_id = '{current_coin}'
                        ORDER BY datetime DESC LIMIT 1;"""
                )
                query = cur.fetchone()
                if query is None:
                    return [
                        i18n.t("value.no_information", current_coin=current_coin),
                        i18n.t("value.no_during_trade"),
                    ]

                balance, usd_price, btc_price, last_update = query
                if balance is None:
                    balance = 0
                if usd_price is None:
                    usd_price = 0
                if btc_price is None:
                    btc_price = 0
                last_update = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S.%f")

                reports = get_previous_reports()
                reports.reverse()

                days_deltas = [1, 7, 30]
                return_rates = []
                amount_btc_now = balance * btc_price
                ts_now = int(last_update.timestamp())
                delta = days_deltas[0]
                for report in reports:
                    if ts_now - report["time"] > timedelta(days=delta).total_seconds():
                        if (
                            ts_now
                            - report["time"]
                            - timedelta(days=delta).total_seconds()
                            < timedelta(hours=2).total_seconds()
                            and report["total_usdt"] > 0
                        ):
                            amount_btc_old = (
                                report["total_usdt"] / report["tickers"]["BTC"]
                            )
                            rate = (amount_btc_now - amount_btc_old) / amount_btc_old
                            rate_str = "+" if rate >= 0 else ""
                            rate_str += str(round(rate * 100, 2))
                            rate_str += " %"
                        else:
                            rate_str = "N/A"
                        return_rates.append(rate_str)
                        if len(return_rates) == len(days_deltas):
                            break
                        delta = days_deltas[len(return_rates)]
                return_rates += ["N/A"] * (len(days_deltas) - len(return_rates))

            except Exception as e:
                logger.error(
                    f"❌ Unable to fetch current coin information from database: {e}",
                    exc_info=True,
                )
                con.close()
                return [
                    i18n.t("value.db_error"),
                    i18n.t("value.no_during_trade"),
                ]

            try:
                m_list = [
                    f"\n{i18n.t('value.last_update', update=last_update.strftime('%H:%M:%S %d/%m/%Y'))}\n\n",
                    f"{i18n.t('value.current_coin', coin=current_coin)}\n",
                    "`",
                    f"{i18n.t('value.balance', balance=balance, coin=current_coin)}\n",
                    f"{i18n.t('value.exchange_rate_purchased', rate=float_strip(buy_price / alt_amount, 8), bridge=bridge, coin=current_coin)}\n",
                    f"{i18n.t('value.exchange_rate_now', rate=float_strip(usd_price, 8), coin=current_coin)}\n",
                    f"{i18n.t('value.value_change', change=round((balance * usd_price - buy_price) / buy_price * 100, 2))}\n",
                    f"{i18n.t('value.value_usd', value=round(balance * usd_price, 2))}\n",
                    f"{i18n.t('value.value_btc', value=float_strip(balance * btc_price, 8))}\n",
                    f"{i18n.t('value.bought_for', value=round(buy_price, 2), coin=bridge)}\n",
                ]
                for i_delta, delta in enumerate(days_deltas):
                    m_list.append(
                        i18n.t(
                            "value.change_btc",
                            days=delta,
                            spaces=" " * max(0, 2 - len(str(delta))),
                            value=return_rates[i_delta],
                        )
                        + "\n"
                    )
                m_list[-1] += "`"

                message = telegram_text_truncator(m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Something went wrong, unable to generate value at this time: {e}",
                    exc_info=True,
                )
                con.close()
                return [i18n.t("value.error")]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("value.db_error")]
    return message


def check_progress():
    logger.info("Progress button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    message = [i18n.t("database_not_found", path=db_file_path)]
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
                m_list = [f"{i18n.t('progress.coin')}\n\n"]
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
                            "progress.change_over_days",
                            amount=coin[3],
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
                        f"\t{i18n.t('progress.amount', amount=coin[1], coin=coin[0])}\n"
                        f"\t{i18n.t('progress.price', amount=round(coin[2], 2))}\n"
                        f"\t{change}\n"
                        f"\t{i18n.t('progress.trade_datetime', date=last_trade_date)}\n\n"
                    )

                message = telegram_text_truncator(m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Unable to fetch progress information from database: {e}",
                    exc_info=True,
                )
                con.close()
                return [i18n.t("progress.db_error")]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("progress.db_error")]
    return message


def current_ratios():
    logger.info("Current ratios button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    message = [i18n.t("database_not_found", path=db_file_path)]
    if os.path.exists(db_file_path):
        try:
            # Get bridge currency symbol
            with open(user_cfg_file_path) as cfg:
                config = ConfigParser()
                config.read_file(cfg)
                bridge = config.get("binance_user_config", "bridge")
                scout_multiplier = config.get("binance_user_config", "scout_multiplier")
                try:  # scout_margin Edgen
                    scout_margin = (
                        float(config.get("binance_user_config", "scout_margin")) / 100.0
                    )
                    use_margin = config.get("binance_user_config", "use_margin")
                except Exception as e:
                    use_margin = "no"
                try:  # scout_margin TnTwist
                    ratio_calc = config.get("binance_user_config", "ratio_calc")
                except Exception as e:
                    ratio_calc = "default"
                if ratio_calc == "scout_margin":
                    scout_multiplier = float(scout_multiplier) / 100.0

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
                return [i18n.t("ratios.db_error")]

            # Get prices and ratios of all alt coins
            try:
                if use_margin == "yes":  # scout_margin Edgen
                    logger.info(f"Margin ratio Edgen")
                    cur.execute(
                        f"""SELECT sh.datetime, p.to_coin_id, sh.other_coin_price, ((1+0.001*0.001-0.002) * current_coin_price/other_coin_price / sh.target_ratio - 1 - {scout_margin}) AS 'ratio_dict' FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id='{current_coin}' AND p.from_coin_id = ( SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC LIMIT ( SELECT count(DISTINCT pairs.to_coin_id) FROM pairs JOIN coins ON coins.symbol = pairs.to_coin_id WHERE coins.enabled = 1 AND pairs.from_coin_id='{current_coin}');"""
                    )
                elif ratio_calc == "scout_margin":  # scout_margin TnTwist
                    logger.info(f"Margin ratio TnTwist")
                    cur.execute(
                        f"""SELECT sh.datetime, p.to_coin_id, sh.other_coin_price, ((1+0.001*0.001-0.002) * current_coin_price/other_coin_price / sh.target_ratio - 1 - {scout_multiplier}) AS 'ratio2_dict' FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id='{current_coin}' AND p.from_coin_id = ( SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC LIMIT ( SELECT count(DISTINCT pairs.to_coin_id) FROM pairs JOIN coins ON coins.symbol = pairs.to_coin_id WHERE coins.enabled = 1 AND pairs.from_coin_id='{current_coin}');"""
                    )
                else:  # defaultst
                    logger.info(f"Margin ratio default")
                    cur.execute(
                        f"""SELECT sh.datetime, p.to_coin_id, sh.other_coin_price, ( ( ( current_coin_price / other_coin_price ) - 0.001 * '{scout_multiplier}' * ( current_coin_price / other_coin_price ) ) - sh.target_ratio ) AS 'ratio_dict' FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id='{current_coin}' AND p.from_coin_id = ( SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC LIMIT ( SELECT count(DISTINCT pairs.to_coin_id) FROM pairs JOIN coins ON coins.symbol = pairs.to_coin_id WHERE coins.enabled = 1 AND pairs.from_coin_id='{current_coin}');"""
                    )
                query = cur.fetchall()

                # Generate message
                last_update = datetime.strptime(query[0][0], "%Y-%m-%d %H:%M:%S.%f")
                query = sorted(query, key=lambda k: k[-1], reverse=True)

                m_list = [
                    f"\n{i18n.t('ratios.last_update', update=last_update.strftime('%H:%M:%S %d/%m/%Y'))}\n\n"
                    f"{i18n.t('ratios.compared_ratios', coin=current_coin)}\n"
                ]
                max_length_ticker = max([len(i[1]) for i in query] + [4])

                m_list.extend(
                    tabularize(
                        [
                            i18n.t("ratios.coin"),
                            i18n.t("ratios.price", bridge=bridge),
                            i18n.t("ratios.ratio"),
                        ],
                        [[q[1], q[2], q[3]] for q in query],
                        [6, 12, 12],
                        align="left",
                        add_spaces=[True, True, False],
                    )
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
                    i18n.t("ratios.gen_error"),
                    i18n.t("logging_enabled_error"),
                ]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("ratios.db_error")]
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
                try:  # scout_margin Edgen
                    scout_margin = (
                        float(config.get("binance_user_config", "scout_margin")) / 100.0
                    )
                    use_margin = config.get("binance_user_config", "use_margin")
                except Exception as e:
                    use_margin = "no"
                try:  # scout_margin TnTwist
                    ratio_calc = config.get("binance_user_config", "ratio_calc")
                except Exception as e:
                    ratio_calc = "default"
                if ratio_calc == "scout_margin":
                    scout_multiplier = float(scout_multiplier) / 100.0

            con = sqlite3.connect(db_file_path)
            cur = con.cursor()

            # Get prices and percentages for a jump to the next coin
            try:
                if use_margin == "yes":  # scout_margin Edgen
                    logger.info(f"Margin ratio Edgen")
                    cur.execute(
                        f"""SELECT p.to_coin_id as other_coin, sh.other_coin_price, (1-0.001*0.001-0.002) * current_coin_price / (sh.target_ratio *(1+{scout_margin})) AS 'price_needs_to_drop_to', (1-0.001*0.001-0.002) * current_coin_price / (sh.target_ratio *(1+{scout_margin})) / sh.other_coin_price as 'percentage'  FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id = (SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC, percentage DESC LIMIT (SELECT count(DISTINCT pairs.to_coin_id) FROM pairs JOIN coins ON coins.symbol = pairs.to_coin_id WHERE coins.enabled = 1 AND pairs.from_coin_id=(SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1));"""
                    )
                elif ratio_calc == "scout_margin":  # scout_margin TnTwist
                    logger.info(f"Margin ratio TnTwist")
                    cur.execute(
                        f"""SELECT p.to_coin_id as other_coin, sh.other_coin_price, (1-0.001*0.001-0.002) * current_coin_price / (sh.target_ratio *(1+{scout_multiplier})) AS 'price_needs_to_drop_to', (1-0.001*0.001-0.002) * current_coin_price / (sh.target_ratio *(1+{scout_multiplier})) / sh.other_coin_price as 'percentage'  FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id = (SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC, percentage DESC LIMIT (SELECT count(DISTINCT pairs.to_coin_id) FROM pairs JOIN coins ON coins.symbol = pairs.to_coin_id WHERE coins.enabled = 1 AND pairs.from_coin_id=(SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1));"""
                    )
                else:  # default
                    logger.info(f"Margin ratio default")
                    cur.execute(
                        f"""SELECT p.to_coin_id as other_coin, sh.other_coin_price, (current_coin_price - 0.001 * '{scout_multiplier}' * current_coin_price) / sh.target_ratio AS 'price_needs_to_drop_to', ((current_coin_price - 0.001 * '{scout_multiplier}' * current_coin_price) / sh.target_ratio) / sh.other_coin_price as 'percentage' FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id = (SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC, percentage DESC LIMIT (SELECT count(DISTINCT pairs.to_coin_id) FROM pairs JOIN coins ON coins.symbol = pairs.to_coin_id WHERE coins.enabled = 1 AND pairs.from_coin_id=(SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1));"""
                    )
                query = cur.fetchall()
                m_list = []
                query = sorted(query, key=lambda x: x[3], reverse=True)

                m_list.extend(
                    tabularize(
                        [
                            i18n.t("next_coin.coin"),
                            i18n.t("next_coin.percentage"),
                            i18n.t("next_coin.current_price"),
                            i18n.t("next_coin.target_price"),
                        ],
                        [[q[0], str(round(q[3] * 100, 2)), q[1], q[2]] for q in query],
                        [6, 7, 8, 8],
                        add_spaces=[True, True, False, False],
                        align=["center", "left", "left", "left"],
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
                    i18n.t("next_coin.error"),
                    i18n.t("logging_enabled_error"),
                ]
        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("next_coin.db_error")]
    return message


def check_status():
    logger.info("Check status button pressed.")

    message = i18n.t("btb.not_running")
    if get_binance_trade_bot_process():
        message = i18n.t("btb.running")
    return message


def trade_history():
    logger.info("Trade history button pressed.")

    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    message = [i18n.t("database_not_found", path=db_file_path)]
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
                    f"{i18n.t('history.last_x_trades', trades=10 if len(query) > 10 else len(query))}\n\n"
                ]
                for trade in query:
                    if trade[4] is None:
                        continue
                    date = datetime.strptime(trade[6], "%Y-%m-%d %H:%M:%S.%f")
                    if trade[5] is not None:

                        trade_details = i18n.t(
                            "history.sold_bought",
                            sold_trade=i18n.t("history.sold")
                            if trade[2]
                            else i18n.t("history.bought"),
                            amount1=trade[4],
                            coin1=trade[0],
                            amount2=trade[5],
                            coin2=trade[1],
                        )
                    else:
                        trade_details = ""

                    m_list.append(
                        f"`{date.strftime('%H:%M:%S %d/%m/%Y')}`\n"
                        f"{trade_details}\n"
                        f"{i18n.t('history.status', status=trade[3])}\n\n"
                    )

                message = telegram_text_truncator(m_list)
                con.close()
            except Exception as e:
                logger.error(
                    f"❌ Something went wrong, unable to generate trade history at this time: {e}",
                    exc_info=True,
                )
                con.close()
                return [i18n.t("history.error")]

        except Exception as e:
            logger.error(
                f"❌ Unable to perform actions on the database: {e}", exc_info=True
            )
            message = [i18n.t("history.db_error")]
    return message


def bot_stats():
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    if not os.path.exists(db_file_path):
        return [i18n.t("database_not_found", path=db_file_path)]

    message = ""

    stableCoins = ["USDT", "USD", "BUSD", "USDC", "DAI"]

    try:
        con = sqlite3.connect(db_file_path)
        cur = con.cursor()

        cur.execute(
            "SELECT datetime FROM trade_history WHERE selling=0 and state='COMPLETE' ORDER BY id ASC LIMIT 1"
        )
        query = cur.fetchall()
        if len(query) == 0:
            message = [i18n.t("bot_stats.error.date_error")]
            return message
        bot_start_date = query[0][0]

        cur.execute("SELECT datetime FROM scout_history ORDER BY id DESC LIMIT 1")
        query = cur.fetchall()
        if len(query) == 0:
            message = [i18n.t("bot_stats.error.date_error")]
            return message
        bot_end_date = query[0][0]

        cur.execute("SELECT * FROM trade_history ")
        lenTradeHistory = len(cur.fetchall())
        if not lenTradeHistory > 0:
            message = [i18n.t("bot_stats.error.empty_trade_history")]
            return message

        cur.execute("SELECT count(*) FROM trade_history WHERE selling=0")
        numCoinJumps = cur.fetchall()[0][0]

        start_date = datetime.strptime(bot_start_date[2:], "%y-%m-%d %H:%M:%S.%f")
        end_date = datetime.strptime(bot_end_date[2:], "%y-%m-%d %H:%M:%S.%f")
        numDays = (end_date - start_date).days

        # get first trade and its bridge - all stats must be in this bridge
        cur.execute(
            f"""SELECT alt_coin_id, crypto_coin_id, alt_trade_amount, crypto_trade_amount
            FROM 'trade_history' WHERE state='COMPLETE' ORDER BY id ASC LIMIT 1;"""
        )
        query = cur.fetchone()
        if query is None:
            logger.error(i18n.t("bot_stats.error.first_coin_error"))
            message = [i18n.t("bot_stats.error.first_coin_error")]
            return message
        (
            initialCoinID,
            initialCoinbridgeID,
            initialCoinAmount,
            initialCoinFiatValue,
        ) = query

        cur.execute(
            f"""SELECT alt_coin_id, alt_trade_amount
            FROM 'trade_history'
            WHERE selling=0 and state='COMPLETE'
            ORDER BY id DESC LIMIT 1;"""
        )
        query = cur.fetchone()
        if query is None:
            logger.error(i18n.t("bot_stats.error.current_coin_error"))
            message = [i18n.t("bot_stats.error.current_coin_error")]
            return message
        currentCoinID, currentCoinAmount = query

        cur.execute(
            """
        SELECT min(usd_values), max(usd_values), min(btc_values), max(btc_values) FROM (
            SELECT (balance * usd_price) usd_values, (balance * btc_price) btc_values FROM coin_value WHERE usd_values > 5
        )
        """
        )
        query = cur.fetchone()
        if query is None:
            max_usd = min_usd = max_btc = min_btc = 0
            logger.error("Exception : Unable to calculate min/max USD, BTC values.")
        else:
            min_usd, max_usd, min_btc, max_btc = query

        displayCurrency = (
            "$" if initialCoinbridgeID in stableCoins else initialCoinbridgeID
        )

        if initialCoinbridgeID in stableCoins:
            initialCoinLiveBridgePrice = get_current_price(initialCoinID, "USDT")
            currentCoinLiveBridgePrice = get_current_price(currentCoinID, "USDT")
        else:
            initialCoinLiveBridgePrice = get_current_price(
                initialCoinID, "USDT"
            ) / get_current_price(initialCoinbridgeID, "USDT")
            currentCoinLiveBridgePrice = get_current_price(
                currentCoinID, "USDT"
            ) / get_current_price(initialCoinbridgeID, "USDT")

        initialCoinLiveBridgeValue = (
            initialCoinAmount * initialCoinLiveBridgePrice
        )  # buy & hold value

        currentCoinLiveBridgeValue = currentCoinAmount * currentCoinLiveBridgePrice

        convertibleStartCoinAmount = (
            currentCoinLiveBridgeValue / initialCoinLiveBridgePrice
        )

        # always show profit in bot start coin's Bridge
        changeFiat = (
            (currentCoinLiveBridgeValue - initialCoinFiatValue)
            / initialCoinFiatValue
            * 100
        )

        changeStartCoin = (
            (convertibleStartCoinAmount - initialCoinAmount) / initialCoinAmount * 100
        )

        message += (
            "`"
            f"{i18n.t('bot_stats.bot_started', date=start_date.strftime('%d/%m/%y'), no_days=numDays)}"
            f"\n{i18n.t('bot_stats.nb_jumps')} {numCoinJumps} ({round(numCoinJumps / max(numDays,1),1)} jumps/day)"
            f"\n{i18n.t('bot_stats.start_coin')} {float_strip(initialCoinAmount, 8)} {initialCoinID} / {round(initialCoinFiatValue, 2)} {displayCurrency}"
            f"\n{i18n.t('bot_stats.current_coin')} {float_strip(currentCoinAmount, 8)} {currentCoinID} / {round(currentCoinLiveBridgeValue, 2)} {displayCurrency}"
            f"\n{i18n.t('bot_stats.profit')} {'+' if changeStartCoin >= 0 else ''}{round(changeStartCoin, 2)}% {initialCoinID} / {'+' if changeFiat >= 0 else ''}{round(changeFiat, 2)}% {displayCurrency}"
            f"\n{i18n.t('bot_stats.hodl')} {float_strip(initialCoinAmount, 8)} {initialCoinID} / {round(initialCoinLiveBridgeValue, 2)} {displayCurrency}"
            f"\n{i18n.t('bot_stats.min_max_usd')} {round(min_usd,2)} / {round(max_usd,2)}"
            f"\n{i18n.t('bot_stats.min_max_btc')} {float_strip(min_btc,8)} / {float_strip(max_btc,8)}"
            "`"
        )

        rows = []
        for coin in settings.COIN_LIST:
            cur.execute(
                f"SELECT COUNT(*) FROM trade_history WHERE alt_coin_id='{coin}' and selling=0 and state='COMPLETE'"
            )
            query = cur.fetchall()
            if len(query) == 0:
                continue
            jumps = query[0][0]

            cur.execute(
                f"SELECT datetime, alt_trade_amount FROM trade_history WHERE alt_coin_id='{coin}' and state='COMPLETE' ORDER BY id ASC LIMIT 1"
            )
            query = cur.fetchall()
            if len(query) == 0:
                continue
            first_date, first_value = query[0]

            cur.execute(
                f"SELECT alt_trade_amount FROM trade_history WHERE alt_coin_id='{coin}' and selling=0 and state='COMPLETE' ORDER BY id DESC LIMIT 1"
            )
            query = cur.fetchall()
            if len(query) == 0:
                continue
            last_value = query[0][0]

            grow = (last_value - first_value) / first_value * 100
            rows.append(
                [
                    coin,
                    float(first_value),
                    float(last_value),
                    str(round(grow, 2)) if grow != 0 else "0",
                    str(jumps),
                ]
            )

        if len(rows) == 0:
            message += f"\n\n{i18n.t('bot_stats.error.empty_trade_history')}\n"
            message = [message]

        else:
            table = tabularize(
                [
                    i18n.t("bot_stats.table.coin"),
                    i18n.t("bot_stats.table.from"),
                    i18n.t("bot_stats.table.to"),
                    "% ±",
                    "<->",
                ],
                rows,
                [4, 8, 8, 8, 3],
                add_spaces=False,
                align=["left", "right", "right", "right", "right"],
            )
            message += f"\n\n*{i18n.t('bot_stats.coin_progress')}*\n"
            message = [message]
            message += table

        message = telegram_text_truncator(message)
    except Exception as e:
        logger.error(f"❌ Unable to perform actions on the database: {e}", exc_info=True)
        message = [i18n.t("bot_stats.error.db_error")]
    return message


def start_bot():
    status = 0  # bot already running
    if not get_binance_trade_bot_process():
        if os.path.isfile(settings.PYTHON_PATH):
            if os.path.exists(os.path.join(settings.ROOT_PATH, "binance_trade_bot/")):
                setup_coin_list()
                subprocess.call(
                    f"cd {settings.ROOT_PATH} && {settings.PYTHON_PATH} -m binance_trade_bot &",
                    shell=True,
                )
                time.sleep(5)  # wait five seconds to let the bot start
                if get_binance_trade_bot_process():
                    status = 1  # bot started
                else:
                    status = 2  # bot start error
            else:
                status = 3  # installation path error
        else:
            status = 4  # python lib error
    return status


def stop_bot():
    logger.info("Stop bot button pressed.")

    message = i18n.t("btb.not_running")
    if get_binance_trade_bot_process():
        find_and_kill_binance_trade_bot_process()
        if not get_binance_trade_bot_process():
            message = i18n.t("btb.stopped")
        else:
            message = f"{i18n.t('btb.stop_error')}\n\n" f"{i18n.t('btb.windows_hint')}"
    return message


def read_log():
    logger.info("Read log button pressed.")

    log_file_path = os.path.join(settings.ROOT_PATH, "logs/crypto_trading.log")
    message = f"{i18n.t('log.error', path=log_file_path)}"
    if os.path.exists(log_file_path):
        with open(log_file_path) as f:
            file_content = f.read()[-4000:]
            message = (
                f"{i18n.t('log.last_4000_characters')}\n\n"
                f"```\n"
                f"{file_content}\n"
                f"```"
            )
    return message


def delete_db():
    logger.info("Delete database button pressed.")

    message = i18n.t("db.delete.stop_bot")
    delete = False
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    if not get_binance_trade_bot_process():
        if os.path.exists(db_file_path):
            message = i18n.t("db.delete.sure")
            delete = True
        else:
            message = f"{i18n.t('database_not_found', path=db_file_path)}"
    return [message, delete]


def edit_user_cfg():
    logger.info("Edit user configuration button pressed.")

    message = i18n.t("config.stop_bot")
    edit = False
    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    if not get_binance_trade_bot_process():
        if os.path.exists(user_cfg_file_path):
            with open(user_cfg_file_path) as f:
                message = (
                    f"{i18n.t('config.is')}\n\n"
                    f"```\n"
                    f"{f.read()}\n"
                    f"```\n\n"
                    f"{i18n.t('config.reply')}\n\n"
                    f"{i18n.t('stop_to_stop')}"
                )
                edit = True
        else:
            message = f"{i18n.t('config.error', path=user_cfg_file_path)}"
    return [message, edit]


def edit_coin():
    logger.info("Edit coin list button pressed.")

    message = i18n.t("coin_list.stop_bot")
    edit = False
    coin_file_path = os.path.join(settings.ROOT_PATH, "supported_coin_list")
    if not get_binance_trade_bot_process():
        if os.path.exists(coin_file_path):
            with open(coin_file_path) as f:
                message = (
                    f"{i18n.t('coin_list.is')}\n\n"
                    f"```\n{f.read()}\n```\n\n"
                    f"{i18n.t('coin_list.reply')}\n\n"
                    f"{i18n.t('stop_to_stop')}"
                )
                edit = True
        else:
            message = f"{i18n.t('coin_list.not_found', path=coin_file_path)}"
    return [message, edit]


def export_db():
    logger.info("Export database button pressed.")

    message = i18n.t("db.export.stop_bot")
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    file = None
    if not get_binance_trade_bot_process():
        if os.path.exists(db_file_path):
            with open(db_file_path, "rb") as db:
                file = db.read()
            message = i18n.t("db.export.file")
        else:
            message = i18n.t("db.export.error")
    return [message, file]


def update_tg_bot():
    logger.info("⬆ Update Telegram Bot button pressed.")

    message = i18n.t("update.tgb.up_to_date")
    upd = False
    to_update = is_tg_bot_update_available()
    if to_update is not None:
        if to_update:
            message = f"{i18n.t('update.tgb.available')}\n" f"{i18n.t('update.now')}"
            upd = True
    else:
        message = i18n.t("update.tgb.error")
    return [message, upd]


def update_btb():
    logger.info("⬆ Update Binance Trade Bot button pressed.")

    message = i18n.t("update.btb.up_to_date")
    upd = False
    to_update = is_btb_bot_update_available()
    if to_update is not None:
        if to_update:
            upd = True
            message = f"{i18n.t('update.btb.available')}\n" f"{i18n.t('update.now')}"
    else:
        message = i18n.t("update.btb.error")
    return [message, upd]


def panic_btn():
    logger.info("🚨 Panic Button button pressed.")

    # Check if open orders / not in usd
    db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
    if not os.path.exists(db_file_path):
        return [i18n.t("database_not_found"), -1]

    user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    if not os.path.exists(user_cfg_file_path):
        return [i18n.t("config.not_found"), -1]

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
                        f"{i18n.t('panic.holding', amount1=round(alt_trade_amount, 6), coin1=alt_coin_id, amount2=round(crypto_trade_amount, 2), coin2=crypto_coin_id)}\n\n "
                        f"{i18n.t('panic.rate_when_bought')}\n"
                        f"`{format_float(round(price_old, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('panic.current_rate')}\n"
                        f"`{format_float(round(price_now, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('panic.current_value')}\n"
                        f"`{format_float(round(price_now * alt_trade_amount, 4))}` *{crypto_coin_id}*\n\n"
                        f"{i18n.t('panic.change')}\n"
                        f"`{format_float(round((price_now - price_old) / price_old * 100, 2))}` *%*\n\n"
                        f"{i18n.t('panic.stop_and_sell')}",
                        BOUGHT,
                    ]
                else:
                    con.close()
                    return [
                        f"{i18n.t('panic.open_buy_order', amount1=alt_trade_amount, coin1=alt_coin_id, amount2=crypto_trade_amount, coin2=crypto_coin_id)}\n\n"
                        f"{i18n.t('panic.limit_buy_price')}\n"
                        f"`{format_float(round(price_old, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('panic.current_rate')}\n"
                        f"`{format_float(round(price_now, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('panic.change')}\n"
                        f"`{format_float(round((price_now - price_old) / price_old * 100, 2))}` *%*\n\n"
                        f"{i18n.t('panic.stop_and_cancel')}",
                        BUYING,
                    ]
            else:
                if state == "COMPLETE":
                    con.close()
                    return [
                        f"{i18n.t('panic.order_already_complete', coin=crypto_coin_id)}\n\n"
                        f"{i18n.t('panic.ask_stop_bot')}",
                        SOLD,
                    ]
                else:
                    price_old = crypto_trade_amount / alt_trade_amount
                    price_now = get_current_price(alt_coin_id, crypto_coin_id)
                    con.close()
                    return [
                        f"{i18n.t('panic.open_sell_order', amount1=alt_trade_amount, coin1=alt_coin_id, amount2=crypto_trade_amount, coin2=crypto_coin_id)}\n\n"
                        f"{i18n.t('panic.limit_sell_price')}\n"
                        f"`{format_float(round(price_old, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('panic.current_rate')}\n"
                        f"`{format_float(round(price_now, 4))}` *{crypto_coin_id}*/*{alt_coin_id}*\n\n"
                        f"{i18n.t('panic.change')}\n"
                        f"`{format_float(round((price_now - price_old) / price_old * 100, 2))}` *%*\n\n"
                        f"{i18n.t('panic.stop_and_cancel')}",
                        SELLING,
                    ]

        except Exception as e:
            con.close()
            logger.error(
                f"❌ Something went wrong, the panic button is not working at this time: {e}",
                exc_info=True,
            )
            return [
                i18n.t("panic.error"),
                -1,
            ]
    except Exception as e:
        logger.error(f"❌ Unable to perform actions on the database: {e}", exc_info=True)
        return [i18n.t("panic.db_error"), -1]
