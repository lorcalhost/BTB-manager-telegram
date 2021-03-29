# Binance Trade Bot Manager Telegram
A Telegram bot for remotely managing [Binance Trade Bot].  

**If you have feature requests please open an issue on this repo, developers are also welcome to contribute!**
  
## About
I wanted to develop an easy way of managing [Binance Trade Bot] so that I wouldn't have to constantly ssh into the VPS and my non-techy friends could enjoy the benefits of the bot.  
  
As of now the bot is able to perform the following actions:
- Check bot status (running / not running)
- Start *Binance Trade Bot*
- Stop *Binance Trade Bot*
- Edit coin list (`supported_coin_list` file)
- Edit user configuration (`user.cfg` file)
- Delete database file (`crypto_trading.db` file)
- Display last 4096 characters of log file
- WIP Display gains / current ratios in the database

The program's default behavior fetches Telegram `token` and `user_id` from [Binance Trade Bot]'s `apprise.yaml` file.  
Only the Telegram user with `user_id` equal to the one set in the `apprise.yaml` file will be able to use the bot.

⚠ The program is fully compatible with **Linux** and **Windows** through **[WSL](https://docs.microsoft.com/en-us/windows/wsl/install-win10)**, further compatibility testing needs to done for **native Windows** and **MacOS**.  
## Installation
*Python 3* is required.
1. Install dependencies:
```console
# install required Python 3 modules
$ python3 -m pip install -r requirements.txt
```
2. Move `BTBManagerTelegram.py` file into [Binance Trade Bot]'s installation folder (it should be in the same folder as `supported_coin_list` file)

⚠ Make sure the correct `rwx` permissions are set and the program is run with correct privileges.

## Usage
### **Method 1**: Run directly
**BTBManagerTelegram** can be run directly by executing the following command:
```console
# Run normally
$ python3 BTBManagerTelegram.py

# If the bot is running on a server you may want to keep it running even after ssh connection is closed by using nohup
$ nohup python3 BTBManagerTelegram.py &
```
Make sure  [Binance Trade Bot]'s `apprise.yaml` file is correctly setup before running.
### **Method 2:** Import script
**BTBManagerTelegram** can be imported in your Python script and used in the following way:
```python
from BTBManagerTelegram import BTBManagerTelegram
BTBManagerTelegram()
```
The `BTBManagerTelegram()` class takes the following ***optional*** initialization arguments:
- `root_path`:  
*Default value*: `'./'`  
*Description*: Current base directory, to be used in case the bot has not been put inside [Binance Trade Bot]'s installation folder.
- `from_yaml`:  
*Default value*: `True`  
*Description*: Set to `False` if you **don't** want *BTBManagerTelegram* to automatically fetch Telegram `token` and `user_id` from `apprise.yaml` file.
- `token`:  
*Default value*: `None`  
*Description*: If `from_yaml` is set to `False` this will be used as Telegram `token`.
- `user_id`:  
*Default value*: `None`  
*Description*: If `from_yaml` is set to `False` this will be used as Telegram `user_id`.

## Interaction
Interaction with **BTBManagerTelegram** can be *started* by sending the command `/start` in the bot's Telegram chat.
## Disclaimer

This project is for informational purposes only. You should not construe any
such information or other material as legal, tax, investment, financial, or
other advice. Nothing contained here constitutes a solicitation, recommendation,
endorsement, or offer by me or any third party service provider to buy or sell
any securities or other financial instruments in this or in any other
jurisdiction in which such solicitation or offer would be unlawful under the
securities laws of such jurisdiction.

If you plan to use real money, USE AT YOUR OWN RISK.

Under no circumstances will I be held responsible or liable in any way for any
claims, damages, losses, expenses, costs, or liabilities whatsoever, including,
without limitation, any direct or indirect damages for loss of profits.

##### ⚙ Developed for the love of task automation by [Lorenzo Callegari](https://github.com/lorcalhost)


[Binance Trade Bot]: https://github.com/edeng23/binance-trade-bot
