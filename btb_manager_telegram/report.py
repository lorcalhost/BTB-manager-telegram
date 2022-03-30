import datetime as dt
import os
import shutil
import sys
import time
import traceback
import warnings

import binance
import i18n
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import requests

from btb_manager_telegram import settings
from btb_manager_telegram.formating import escape_tg
from btb_manager_telegram.logging import if_exception_log, logger
from btb_manager_telegram.schedule import scheduler

warnings.filterwarnings("ignore", category=UserWarning)

additional_coins = ["BTC"]
include_only_coinlist = True


def reports_path():
    return os.path.join(settings.ROOT_PATH, "data", "btbmt_reports.npy")


def migrate_reports():
    """
    Used to migrate report placement from v1.1.1 to v1.2
    """

    if os.path.isfile("data/crypto.npy"):
        shutil.move("data/crypto.npy", reports_path())


def build_ticker(all_symbols, tickers_raw):
    backup_coins = ["BTC", "ETH", "BNB"]
    tickers = {"USDT": 1, "USD": 1}
    tickers_raw = {t["symbol"]: float(t["price"]) for t in tickers_raw}
    failed_coins = []

    for symbol in set(backup_coins + all_symbols):
        success = False
        for stable in ("USD", "USDT", "BUSD", "USDC", "DAI"):
            pair = symbol + stable
            if pair in tickers_raw:
                tickers[symbol] = tickers_raw[pair]
                success = True
                break
        if not success:
            failed_coins.append(symbol)

    for symbol in failed_coins:
        success = False
        for b_coin in backup_coins:
            pair = symbol + b_coin
            if pair in tickers_raw:
                tickers[symbol] = tickers_raw[pair] * tickers[b_coin]
                success = True
                break
        if not success:
            logger.debug(f"Could not retreive USD price for {symbol}, skipping")

    return tickers


def get_report():
    api = binance.Client(
        settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET, tld=settings.TLD
    )

    account = api.get_account()
    account_symbols = []
    balances = {}
    for balance in account["balances"]:
        symbol = balance["asset"]

        if symbol.startswith("LD"):
            # skip the coins in binance saving
            # (see https://github.com/titulebolide/binance-report-bot/issues/5)
            continue

        if include_only_coinlist and symbol not in settings.COIN_LIST:
            continue

        qty = float(balance["free"]) + float(balance["locked"])
        if qty != 0:
            account_symbols.append(symbol)
            balances[symbol] = qty

    all_symbols = list(set(settings.COIN_LIST + account_symbols + additional_coins))
    if settings.CURRENCY == "EUR":
        all_symbols.append("EUR")
    tickers_raw = api.get_symbol_ticker()
    tickers = build_ticker(all_symbols, tickers_raw)
    if settings.CURRENCY not in ("USD", "EUR"):
        ticker = (
            1
            / requests.get(
                "https://openexchangerates.org/api/latest.json?app_id="
                + settings.OER_KEY
            ).json()["rates"][settings.CURRENCY]
        )
        tickers[settings.CURRENCY] = ticker

    logger.debug(f"Prices after filtering : {tickers}")

    total_usdt = 0
    for symbol in account_symbols:
        if symbol not in tickers:
            logger.debug(f"{symbol} has no price, skipping")
            continue
        total_usdt += balances[symbol] * tickers[symbol]

    report = {}
    report["total_usdt"] = total_usdt
    report["balances"] = balances
    report["tickers"] = tickers
    return report


def get_previous_reports():
    if os.path.exists(reports_path()):
        reports = np.load(reports_path(), allow_pickle=True).tolist()
        return reports
    else:
        return []


def save_report(report, old_reports):
    report["time"] = int(time.time())
    old_reports.append(report)
    np.save(reports_path(), old_reports, allow_pickle=True)
    return old_reports


def make_snapshot():
    logger.info("Retreive balance information from binance")
    crypto_report = get_report()
    crypto_reports = save_report(crypto_report, get_previous_reports())
    logger.info("Snapshot saved")


def get_graph(relative, symbols, days, graph_type, ref_currency):
    if symbols == ["*"]:
        symbols = settings.COIN_LIST
    else:
        for s in symbols:
            assert s in settings.COIN_LIST + [settings.CURRENCY] + additional_coins
    if len(symbols) > 1:
        relative = True
    reports = get_previous_reports()

    plt.clf()
    plt.close()
    if len(symbols) < 10:
        plt.figure()
    else:
        plt.figure(figsize=(10, 6))

    min_timestamp = 0
    if days != 0:
        min_timestamp = time.time() - days * 24 * 60 * 60

    nb_plot = 0
    for symbol in symbols:
        X, Y = [], []
        for report in reports:
            if report["time"] < min_timestamp:
                continue  # skip if too recent
            if symbol not in report["tickers"]:
                ts = report["time"]
                logger.debug(f"{symbol} has no price in the report with timestamp {ts}")
                continue
            ticker = report["tickers"][symbol]
            if ticker == 0:
                ts = report["time"]
                logger.debug(
                    f"{symbol} has an invalid price in the report with timestamp {ts}"
                )
                continue

            y = None
            if graph_type == "amount":
                y = report["total_usdt"] / ticker
            elif graph_type == "price":
                ref_currency_ticker = 1
                if ref_currency not in ("USD", "USDT"):
                    if ref_currency not in report["tickers"]:
                        continue
                    ref_currency_ticker = report["tickers"][ref_currency]
                    if ref_currency_ticker == 0:
                        continue
                y = ticker / ref_currency_ticker
            if y is None:
                continue

            Y.append(y)
            X.append(dt.datetime.fromtimestamp(report["time"]))
            nb_plot += 1

        if len(Y) == 0:
            continue

        if relative:
            Y = np.array(Y)
            Y = (Y / Y[0] - 1) * 100
        plt.plot(X, Y, label=symbol)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
    plt.setp(plt.xticks()[1], rotation=15)
    if graph_type == "amount":
        if relative:
            plt.ylabel(i18n.t("graph.relative_amount"))
            plt.legend(bbox_to_anchor=(1, 1), loc="upper left")
        else:
            label = i18n.t("graph.amount")
            label += f" ({symbols[0]})" if len(symbols) == 1 else ""
            plt.ylabel(label)
    elif graph_type == "price":
        if relative:
            plt.ylabel(i18n.t("graph.relative_price", currency=ref_currency))
        else:
            plt.ylabel(i18n.t("graph.price", currency=ref_currency))
    plt.grid()
    figname = f"data/quantity_{symbol}.png"
    plt.savefig(figname)
    return figname, nb_plot
