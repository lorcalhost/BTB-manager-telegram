import os
import time
import requests
import binance
import numpy as np
from btb_manager_telegram import logger, scheduler, settings


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

        qty = float(balance["free"]) + float(balance["locked"])
        if qty != 0:
            account_symbols.append(symbol)
            balances[symbol] = qty

    all_symbols = list(set(settings.COIN_LIST + account_symbols))
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
    if os.path.exists("data/crypto.npy"):
        reports = np.load("data/crypto.npy", allow_pickle=True).tolist()
        return reports
    else:
        return []


def save_report(report, old_reports):
    report["time"] = int(time.time())
    old_reports.append(report)
    np.save("data/crypto.npy", old_reports, allow_pickle=True)
    return old_reports


def make_snapshot():
    logger.info("Retreive balance information from binance")
    crypto_report = get_report()
    crypto_reports = save_report(
        crypto_report, get_previous_reports()
    )
    scheduler.enter(3600, 2, make_snapshot)
    logger.info("Snapshot saved")
