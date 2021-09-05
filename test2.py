from binance import Client
import requests
import json
import time

api_key = "d31ap0mQsPawYkHka3TVYHBc1OAMZutUJv6Wlc6LCZbCWC0iGWDliBsDe9SjISw7"
api_secret = "6sa0T8rGH6LlRH7ZkwzvKDO8zRr1qsVW9KAx9Siv7GxYvdgvs0zcVBuSR4cxdPqm"

client = Client(api_key, api_secret)

client.API_URL = "https://api.binance.com/api"

# info = client.get_all_tickers()

# accinfo = client.get_account()

# status = client.get_account_status()

# infso = client.get_account_snapshot(type='SPOT', limit=10)

# balance = client.get_asset_balance(asset='BTC')

accountBalanaces = client.get_account()["balances"]

b = [y for y in accountBalanaces if y["free"] != "0.00000000" and y["free"] != "0.00"]
for item in b:
    if item['asset'] != 'USDT':
        priceToBTC = client.get_avg_price(symbol=item["asset"] + "BTC")["price"]
        item["totalInBTC"] = round(float(priceToBTC),8) * round(float(item["free"]),8)
        btcgpb = client.get_avg_price(symbol="BTCGBP")["price"]
        x = float(btcgpb) * float(item["totalInBTC"])
        item["totalInGBP"] = round(x,2)
x = []
for item in b:
    if item['asset'] != 'USDT':
        x.append(item['totalInGBP'])
print(sum(x))

# dogeDetails = client.get_asset_balance(asset="C98")
# totalDoge = dogeDetails["free"]

# dogebtcDetails = client.get_avg_price(symbol="C98BTC")
# dogebtcPrice = dogebtcDetails["price"]

# doge2btc = round(float(totalDoge),8) * round(float(dogebtcPrice),8)

# dogegbp = client.get_avg_price(symbol="BTCGBP")
# odgegpbprice = dogegbp["price"]

# x = float(doge2btc) * float(odgegpbprice)

# a = round(x,2)

# print(client.get_asset_balance(asset="DOGE"))
# print(client.get_avg_price(symbol="DOGEBTC"))


# print(client.get_latest_crypto_price(crypto='DOGEBTC'))

# # TOTAL_DODGE = 59.1
# # TOTAL_BTC = 0.00034219
# TICKER_API_URL = "https://api.binance.com/api/v3/ticker/price?symbol=DOGEBTC"

# # clear_screen()


# def get_latest_crypto_price(crypto):

#     response = requests.get(TICKER_API_URL + crypto)
#     data = json.loads(response.text)
#     price = float(data["price"])
#     return round(price, 4)


# def main():

#     last_price = -1

#     while True:
#         crypto = "DOGEBTC"
#         price = get_latest_crypto_price(crypto)

#         if price != last_price:
#             print(u"\xA3" + str(price))
#             print(u"\xA3" + str(round(price * TOTAL_DODGE, 2)))
#             last_price = price
#         time.sleep(300)


# main()
