# Binance Trade Bot Manager Telegram

A Telegram bot for remotely managing [Binance Trade Bot].

## About

I wanted to develop an easy way of managing [Binance Trade Bot] so that I wouldn't have to constantly ssh into my VPS, and my non-techy friends could enjoy the benefits of automated trading.

As of now the bot is able to perform the following actions:

- [x] 🔍 Check bot status (running / not running)
- [x] ▶ Start _Binance Trade Bot_
- [x] ⏹ Stop _Binance Trade Bot_
- [x] 💵 Display current coin stats (balance, USD value, BTC value, initial buying price)
- [x] ➗ Display current coin ratios
- [x] 📈 Display progress (how much more of a certain coin you gained since you started using _Binance Trade Bot_)
- [x] ⌛ Display trade history
- [x] 📜 Display last 4000 characters of log file
- [x] 👛 Edit coin list (`supported_coin_list` file)
- [x] ⚙ Edit user configuration (`user.cfg` file)
- [x] ❌ Delete database file (`crypto_trading.db` file)
- [x] 📤 Export database file
- [x] ⬆ **Update** _Binance Trade Bot_ (and notify when new update is available)
- [x] ⬆ **Update** _Binance Trade Bot Manager Telegram_ (and notify when new update is available)
- [x] 🚨 Panic button (Kills _Binance Trade Bot Manager Telegram_ and cancels all open orders / sells at market price)
- [x] [User defined custom scripts](./docs/custom-scripts.md)

</br>

The program's default behavior fetches Telegram `token` and `chat_id` from [Binance Trade Bot]'s `apprise.yml` file.  
Only the Telegram users in the chat with `chat_id` equal to the one set in the `apprise.yml` file will be able to use the bot.

⚠ The program is fully compatible with **Linux** and **Windows** through **[WSL]**;  
`RWX` permission problems are present on **native Windows** and **MacOS**.

## Installation

_Python 3_ is required.  
**BTB-manager-telegram** should be installed in the same parent directory as _Binance Trade Bot_.  
Your filesystem should look like this:

```
.
└── *parent_dir*
    ├── BTB-manager-telegram
    └── binance-trade-bot
```

1. Clone this repository:

```console
$ git clone https://github.com/lorcalhost/BTB-manager-telegram.git
```

2. Move to `BTB-manager-telegram`'s directory:

```console
$ cd BTB-manager-telegram
```

3. Install `BTB-manager-telegram`'s dependencies:

```console
$ python3 -m pip install -r requirements.txt
```

⚠ Make sure the correct `rwx` permissions are set and the program is run with correct privileges.

## Setup

- For a quick Telegram bot setup guide [click here](./docs/telegram-setup.md).
- For a Docker setup guide [click here](./docs/docker-setup.md).
- If you would like to run several _Binance Trade Bot_ instances at the same time [click here](./docs/multiple-bots.md).

Note:  
`BTB-manager-telegram` also supports [user defined custom scripts](./docs/custom-scripts.md).

## Usage

**BTBManagerTelegram** can be run directly by executing the following command:

```console
# Run normally
$ python3 -m btb_manager_telegram

# If the bot is running on a server you may want to keep it running even after ssh connection is closed by using nohup
$ nohup python3 -m btb_manager_telegram &
```

Make sure [Binance Trade Bot]'s `apprise.yml` file is correctly setup before running.  
</br>
Note:  
If _Binance Trade Bot_ and _BTB-Manager-Telegram_ were **not** installed in the same parent directory or you want to use different `token` and `chat_id` from the ones in the `apprise.yml` file, the following optional arguments can be used:

```console
optional arguments:
  -p PATH, --path PATH  (optional) binance-trade-bot installation absolute path
  -t TOKEN, --token TOKEN
                        (optional) Telegram bot token
  -c CHAT_ID, --chat_id CHAT_ID
                        (optional) Telegram chat id
  -d DOCKER, --docker DOCKER
                        (optional) Run the script in a docker container.
                        NOTE: Run the 'docker_setup.py' file before passing this flag.
```

⚠ Please check the [Docker setup] guide if you would like to run the bot in a Docker container.

## Interaction

Interaction with **BTBManagerTelegram** can be _started_ by sending the `/start` command in the bot's Telegram chat.  
Every time the Telegram bot is restarted, the `/start` command should be sent again.

You can also add the bot to a group if multiple people need to access this bot. Please note that each user will have to type `/start` in the group, before they can start interacting with the bot.

## Screenshots

<details><summary>Click here</summary>

<p align="center">
  	<img height="20%" width="20%" src="https://i.imgur.com/9JUN2G7.jpg" />&nbsp;&nbsp;&nbsp;&nbsp;
    <img height="20%" width="20%" src="https://i.imgur.com/FBSNURs.jpg" />&nbsp;&nbsp;&nbsp;&nbsp;
    <img height="20%" width="20%" src="https://i.imgur.com/UKyREe9.jpg" />
</p>
</details>

## [Troubleshooting]

## Support the project

I am currently a broke university student, if you like my work and use it on a daily basis consider supporting the project through a small donation. :smile:

[:heart: Sponsor on GitHub](https://github.com/sponsors/lorcalhost)

<a href="https://www.buymeacoffee.com/lorcalhost">
  <img src="https://img.buymeacoffee.com/button-api/?text=Buy me a beer&emoji=🍺&slug=lorcalhost&button_colour=FFDD00&font_colour=000000&font_family=Lato&outline_colour=000000&coffee_colour=ffffff">
</a>

_Donations through GitHub sponsors will be matched by GitHub (e.g. if you decide to donate 10$, GitHub will add 10$ to the donation)._

## Contributions and feature requests

If you have any feature requests please [open an issue].

Contributions from anyone are welcome! Before opening pull requests please read the [contributing guidelines].

## Disclaimer

This project is for informational purposes only. You should not consider any
such information or other material as legal, tax, investment, financial, or
other advice. Nothing contained here constitutes a solicitation, recommendation,
endorsement, or offer by me or any third party service provider to buy or sell
any securities or other financial instruments in this or in any other
jurisdiction in which such solicitation or offer would be unlawful under the
securities laws of such jurisdiction.

If you plan to use real money, USE AT YOUR OWN RISK.

Under no circumstances will I or the project's maintainers be held responsible or liable in any way for any claims,
damages, losses, expenses, costs, or liabilities whatsoever, including, without limitation, any direct or indirect
damages for loss of profits.

## Contributors ✨

Many people contributed to the project by providing ideas, finding bugs and helping in the development ([Emoji Key ✨](https://allcontributors.org/docs/en/emoji-key)).  
This project follows the [all-contributors] specification.

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://lorcalhost.com"><img src="https://avatars.githubusercontent.com/u/9640455?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Lorenzo Callegari 乐子睿</b></sub></a><br /><a href="#infra-lorcalhost" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/lorcalhost/test/commits?author=lorcalhost" title="Tests">⚠️</a> <a href="https://github.com/lorcalhost/test/commits?author=lorcalhost" title="Code">💻</a> <a href="https://github.com/lorcalhost/test/commits?author=lorcalhost" title="Documentation">📖</a> <a href="#maintenance-lorcalhost" title="Maintenance">🚧</a> <a href="https://github.com/lorcalhost/test/issues?q=author%3Alorcalhost" title="Bug reports">🐛</a> <a href="#ideas-lorcalhost" title="Ideas, Planning, & Feedback">🤔</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

[binance trade bot]: https://github.com/edeng23/binance-trade-bot
[wsl]: https://docs.microsoft.com/en-us/windows/wsl/install-win10
[troubleshooting]: ./docs/troubleshooting.md
[docker setup]: ./docs/docker-setup.md
[open an issue]: https://github.com/lorcalhost/BTB-manager-telegram/issues/new
[contributing guidelines]: ./CONTRIBUTING.md
[all-contributors]: https://github.com/all-contributors/all-contributors
