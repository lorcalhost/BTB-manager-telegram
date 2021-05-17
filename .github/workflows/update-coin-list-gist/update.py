"""
Script adapted from kentwar's binance_correlation_script
https://github.com/kentwar/binance_correlation_script
"""

import os
from datetime import datetime, timedelta

import pandas as pd
from binance.client import Client

api_key = os.environ.get("BINANCE_API_KEY")
api_secret = os.environ.get("BINANCE_API_SECRET_KEY")
client = Client(api_key, api_secret)


def get_ticker_price(ticker_symbol: str, days: int, granularity: str):
    """
    Gets ticker price of a specific coin
    """

    target_date = (datetime.now() - timedelta(days=days)).strftime("%d %b %Y %H:%M:%S")
    key = f"{ticker_symbol}"
    end_date = datetime.now()
    end_date = end_date.strftime("%d %b %Y %H:%M:%S")

    coindata = pd.DataFrame(columns=[key])

    prices = []
    dates = []
    for result in client.get_historical_klines(
        ticker_symbol, granularity, target_date, end_date, limit=1000
    ):
        date = datetime.utcfromtimestamp(result[0] / 1000).strftime("%d %b %Y %H:%M:%S")
        price = float(result[1])
        dates.append(date)
        prices.append(price)

    coindata[key] = prices
    coindata["date"] = dates

    return coindata.reindex(columns=["date", key])


def get_price_data(tickers, window=1, granularity="1m"):
    """
    Collects price data from the binance server.
    """
    failures = []
    coindata = get_ticker_price(tickers[0], window, granularity)
    for tick in tickers[1:]:
        newdata = get_ticker_price(tick, window, granularity)
        if not newdata.empty:
            coindata = pd.merge(coindata, newdata)
        else:
            failures.append(tick)
    print("The following coins do not have historical data")
    print(failures)
    return coindata


def take_rolling_average(coindata):

    RA = pd.DataFrame()

    for column in coindata:
        if column != "date":
            RA[column] = coindata[column].rolling(window=3).mean()
    return RA


def pick_coins(start_ticker, day_corr, week_corr, two_week_corr, n):
    """
    Takes your starting coin, then sequentially picks the coin that jointly maximises
    the correlation for the whole coin list.

    INPUT:
    start_ticker : STR : The ticker for a coin you wish to include in your list
    day_corr     : PD.CORR : daily correlation data
    week_corr    : PD.CORR : Weekly correlation data
    two_week_corr: PD.CORR : bi-weekly correlation data
    n            : INTEGER : number of coins to include in your list.
    """

    coinlist = [start_ticker]
    for i in range(n - 1):
        new_day_corr = day_corr[~day_corr.index.isin(coinlist)]
        new_week_corr = week_corr[~week_corr.index.isin(coinlist)]
        new_two_week_corr = two_week_corr[~two_week_corr.index.isin(coinlist)]
        corrsum = pd.DataFrame()
        for coin in coinlist:
            if corrsum.empty:
                corrsum = (
                    new_day_corr[coin] + new_week_corr[coin] + new_two_week_corr[coin]
                )
            else:
                corrsum += (
                    new_day_corr[coin] + new_week_corr[coin] + new_two_week_corr[coin]
                )

        ind = corrsum.argmax()
        coinlist.append(new_day_corr.index[ind])
    return coinlist


#! Choose your Bridge coin and Starting coin here

bridge = "USDT"
startcoin = "QTUM"
size_of_list = 10

client = Client(api_key, api_secret)

# Download ALL the coinpairs from binance
exchange_info = client.get_exchange_info()

full_coin_list = []

# Only keep the pairs to our bridge coin
for s in exchange_info["symbols"]:
    if s["symbol"].endswith(bridge):
        full_coin_list.append(s["symbol"][:-4])

# List of words to eliminate futures markets coins
forbidden_words = ["DOWN", "UP", "BULL", "BEAR"]
for forbidden in forbidden_words:
    full_coin_list = [word for word in full_coin_list if forbidden not in word]

# Alphabetical order because pretty :)
full_coin_list.sort()

# Collect the data for 3 different windows (1 day, 1 week, 2 weeks)
# with granularity (1 minute, 1 hour ,2 hours)

cointickers = [coin + bridge for coin in full_coin_list]
day_data = get_price_data(cointickers, 1, "1m")
week_data = get_price_data(cointickers, 7, "1h")
two_week_data = get_price_data(cointickers, 14, "2h")

# Calculate the rolling average (RA3) for all the coins

RA_day_data = take_rolling_average(day_data)
RA_week_data = take_rolling_average(week_data)
RA_2week_data = take_rolling_average(two_week_data)

# take the correlations of the rolling averages.

day_corr = RA_day_data.corr()
week_corr = RA_week_data.corr()
two_week_corr = RA_2week_data.corr()

coinlist = pick_coins(
    startcoin + bridge, day_corr, week_corr, two_week_corr, size_of_list
)

#! TACCL Result

coins = [coin.replace(bridge, "") for coin in coinlist]
print(coins)
