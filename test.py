from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager


client = Client(
    "d31ap0mQsPawYkHka3TVYHBc1OAMZutUJv6Wlc6LCZbCWC0iGWDliBsDe9SjISw7",
    "6sa0T8rGH6LlRH7ZkwzvKDO8zRr1qsVW9KAx9Siv7GxYvdgvs0zcVBuSR4cxdPqm",
)
data = client.get_account()["balances"]
data2 = client.get_account()
balance = client.get_asset_balance(asset='BTC')
info = client.get_account_snapshot(type='SPOT')
info2 = client.get_exchange_info()
info3 = client.get_symbol_info('BNBBTC')
avg_price = client.get_avg_price(symbol='BNBBTC')



populated = filter(lambda c: c["free"] != "0.00000000" and c["free"] != "0.00", data)

a = list(populated)

for item in a:
    item
    
# print(a)




# print(list(populated))
