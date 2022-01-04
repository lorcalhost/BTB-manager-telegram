import sqlite3
from datetime import datetime
from sqlite3 import Error

from prettytable import *
from prettytable import PrettyTable

DB_FILE = "./data/crypto_trading.db"

try:
    cursor = sqlite3.connect(DB_FILE)

    db = cursor.cursor()

    db.execute("select symbol from coins where enabled=1")
    coinList = db.fetchall()  # access with coinList[Index][0]
    numCoins = len(coinList)

    db.execute(
        "SELECT datetime FROM trade_history where selling=0 and state='COMPLETE' order by id asc limit 1"
    )
    bot_start_date = db.fetchall()[0][0]

    db.execute("SELECT datetime FROM scout_history order by id desc limit 1")
    bot_end_date = db.fetchall()[0][0]

    db.execute("SELECT * FROM trade_history ")
    lenTradeHistory = len(db.fetchall())

    db.execute(
        "SELECT alt_coin_id FROM trade_history where id=1 and state='COMPLETE' order by id asc limit 1"
    )
    firstTradeCoin = db.fetchall()[0][0]

    initialCoinID = ""
    for i in range(1, lenTradeHistory):
        db.execute(
            "SELECT alt_coin_id FROM trade_history where id='{}' and state='COMPLETE' order by id asc limit 1".format(
                i
            )
        )
        coinID = db.fetchall()
        if len(coinID) > 0:
            coinID = coinID[0][0]
        else:
            continue
        for coin in coinList:
            if coinID == coin[0]:
                initialCoinID = coinID
                db.execute(
                    "select alt_trade_amount from trade_history where alt_coin_id='{}' and state='COMPLETE' order by id asc limit 1".format(
                        initialCoinID
                    )
                )
                initialCoinValue = db.fetchall()[0][0]

                db.execute(
                    "select crypto_trade_amount from trade_history where alt_coin_id='{}' and state='COMPLETE' order by id asc limit 1".format(
                        initialCoinID
                    )
                )
                initialCoinFiatValue = db.fetchall()[0][0]
                break
        if initialCoinID != "":
            break

    db.execute(
        "select alt_coin_id from trade_history where selling=0 and state='COMPLETE' order by id desc limit 1"
    )
    lastCoinID = db.fetchall()[0][0]

    db.execute(
        "select alt_trade_amount from trade_history where selling=0 and state='COMPLETE' order by id desc limit 1"
    )
    lastCoinValue = db.fetchall()[0][0]

    db.execute(
        "select current_coin_price from scout_history order by rowid desc limit 1"
    )
    lastCoinUSD = db.fetchall()[0][0]

    lastCoinFiatValue = lastCoinValue * lastCoinUSD

    if lastCoinID != initialCoinID and initialCoinID != "":
        db.execute(
            "select id from pairs where from_coin_id='{}' and to_coin_id='{}'".format(
                lastCoinID, initialCoinID
            )
        )
        pairID = db.fetchall()[0][0]
        db.execute(
            "select other_coin_price from scout_history where pair_id='{}' order by id desc limit 1".format(
                pairID
            )
        )
        currentValInitialCoin = db.fetchall()[0][0]
    else:
        db.execute(
            "select current_coin_price from scout_history order by id desc limit 1"
        )
        currentValInitialCoin = lastCoinUSD

    if initialCoinID != "":
        imgStartCoinFiatValue = initialCoinValue * currentValInitialCoin
        imgStartCoinValue = lastCoinFiatValue / currentValInitialCoin
        imgPercChangeCoin = (
            (imgStartCoinValue - initialCoinValue) / initialCoinValue * 100
        )

        percChangeFiat = (
            (lastCoinFiatValue - imgStartCoinFiatValue) / imgStartCoinFiatValue * 100
        )

    # No of Days calculation
    start_date = datetime.strptime(bot_start_date[2:], "%y-%m-%d %H:%M:%S.%f")
    end_date = datetime.strptime(bot_end_date[2:], "%y-%m-%d %H:%M:%S.%f")
    numDays = (end_date - start_date).days
    if numDays == 0:
        numDays = 1

    db.execute("select count(*) from trade_history where selling=0")
    numCoinJumps = db.fetchall()[0][0]

    msg = "Bot Started  : {}".format(start_date.strftime("%m/%d/%Y, %H:%M:%S"))
    msg += "\nNo of Days   : {}".format(numDays)
    msg += "\nNo of Jumps  : {} ({:.1f} jumps/day)".format(
        numCoinJumps, numCoinJumps / numDays
    )
    if initialCoinID != "":
        msg += "\nStart Coin   : {:.4f} {} <==> ${:.3f}".format(
            initialCoinValue, initialCoinID, initialCoinFiatValue
        )
    else:
        msg += "\nStart Coin   : -- <==> --"
    msg += "\nCurrent Coin : {:.4f} {} <==> ${:.3f}".format(
        lastCoinValue, lastCoinID, lastCoinFiatValue
    )

    if initialCoinID != "":
        msg += "\nHODL         : {:.4f} {} <==> ${:.3f}".format(
            initialCoinValue, initialCoinID, imgStartCoinFiatValue
        )
        msg += "\n\nApprox Profit: {:.2f}% in USD".format(percChangeFiat)
    else:
        msg += "\nHODL         : -- <==> --"

    if lastCoinID != initialCoinID and initialCoinID != "":
        msg += "\n{} can be approx converted to {:.2f} {}".format(
            lastCoinID, imgStartCoinValue, initialCoinID
        )

    if firstTradeCoin != "" and firstTradeCoin != initialCoinID:
        msg += f"\nBot start coin is {firstTradeCoin} but currently not found in supported list."
    elif initialCoinID == "":
        msg += "\nBot start coin not found in supported list."

    print(msg)

    print("\n:: Coin progress ::")
    x = PrettyTable()
    x.field_names = ["Coin", "From", "To", "%+-", "<->"]

    multiTrades = 0
    # Compute Mini Coin Progress
    for coin in coinList:
        jumps = db.execute(
            f"select count(*) from trade_history where alt_coin_id='{coin[0]}' and selling=0 and state='COMPLETE'"
        ).fetchall()[0][0]
        if jumps > 0:
            multiTrades += jumps
            first_date = db.execute(
                f"select datetime from trade_history where alt_coin_id='{coin[0]}' and selling=0 and state='COMPLETE' order by id asc limit 1"
            ).fetchall()[0][0]
            first_value = db.execute(
                f"select alt_trade_amount from trade_history where alt_coin_id='{coin[0]}' and selling=0 and state='COMPLETE' order by id asc limit 1"
            ).fetchall()[0][0]
            last_value = db.execute(
                f"select alt_trade_amount from trade_history where alt_coin_id='{coin[0]}' and selling=0 and state='COMPLETE' order by id desc limit 1"
            ).fetchall()[0][0]
            grow = (last_value - first_value) / first_value * 100
            x.add_row(
                [
                    coin[0],
                    "{:.2f}".format(first_value),
                    "{:.2f}".format(last_value),
                    "{:.1f}".format(grow),
                    "{}".format(jumps),
                ]
            )

    x.align = "l"
    print(x)
except sqlite3.Error as er:
    print("SQLite error: %s" % (" ".join(er.args)))
