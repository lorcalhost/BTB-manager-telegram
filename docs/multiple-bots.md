# Multiple bots setup

If you have multiple _Binance Trade Bot_ instances running at the same time on the same VPS, a Telegram bot should be created for each instance.

</br>

Two or more `BTB-manager-telegram` instances cannot use the same telegram token.

</br>

The simplest way of running several instances is specifying the path to each of them:

```console
$ python3 -m btb_manager_telegram -p "path/to/bot/1"

$ python3 -m btb_manager_telegram -p "path/to/bot/2"
.
.
.
$ python3 -m btb_manager_telegram -p "path/to/bot/N"
```
