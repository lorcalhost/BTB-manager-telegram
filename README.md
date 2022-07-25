# Binance Trade Bot Manager Telegram

A Telegram bot for remotely managing Edendg23's [Binance Trade Bot](https://github.com/edeng23/binance-trade-bot) and its forks ([Idkravitz's](https://github.com/idkravitz/binance-trade-bot), [Tntwist's](https://github.com/tntwist/binance-trade-bot), [MasaiasuOse's](https://github.com/MasaiasuOse/binance-trade-bot) being the major forks).

This program aims to be an easy way of managing Binance Trade Bot so that I wouldn't have to constantly ssh into my VPS, and my non-techy friends could enjoy the benefits of automated trading.

This program supports only Linux and WSL. Other distributions (BSD, MacOS, Windows, ...) are unmainted and support is not currently planned and is supposed to run 24/7. If you can't have a long running computer on linux, you can use a free VPS, such as Oracle Cloud's.

##  Manual install
**Python 3.7, 3.8 or 3.9** is required.

### 0 - Create a dedicated folder
Create a dedicated directory for the binance trade bot and the present manager. In this tutorial, we will be using **as an example** the folder `~/trading-bot`:
```bash
cd ~
mkdir trading-bot
```

### 1 - Install binance trade bot.
Choose the fork you want to use. The main one ([Edendg23's](https://github.com/edeng23/binance-trade-bot)) is fine to go with.

Place youself in the previously created directory, e.g.:
```bash
cd ~/trading-bot
```

Then follow the install instruction given on the binance-trade-bot's readme. **Setup telegram bot during the install of binance-trade-bot (see the section `Notifications with Apprise` in the README)**

Once the binance-trade-bot has been installed, make sure everything is properly installed : the following commands should yeild no errors.
```
cd ~/trading-bot
ls binance-trade-bot/binance_trade_bot/__main__.py
ls binance-trade-bot/config/apprise.yml
```

### 2 - Install the telegram manager next to the binance trade bot
As always, place youself in the install directory, e.g.:
```bash
cd ~/trading-bot
```

Then, run the following lines:
```console
git clone https://github.com/lorcalhost/BTB-manager-telegram.git
cd BTB-manager-telegram
python3 -m pip install -r requirements.txt
```

## Other Install Methods
### Automated Install
For an automated install, please refer to [Enriko82's Install Script](https://github.com/Enriko82/BTB-Install-script)

### Docker Install
**This method is discouraged as it is no longer maintained.**
*If you crave to contain the bot and its manager, you can always use python's virtual environments.*
However, you can still find a docker setup guide [here](./docs/docker-setup.md).

## Usage
As the telegram bot is launching itself the **Binance Trade Bot**, you only have to start the **BTB Manager Telegram** like so:

```console
python3 -m btb_manager_telegram
```

If the bot is running on a server you may want to keep it running even after ssh connection is closed by using nohup. Note the trailing "&" :
```console
nohup python3 -m btb_manager_telegram &
```

However, you can run the bot with options :
```console
# Autostart the Binance Trade Bot when the BTB Manager starts
# (Otherwise you will have to manually start the Binance Trade Bot from telegram)
python3 -m btb_manager_telegram -s

# Use the french translation. Available translation : en, ru, fr, de, nl, es, id, cn, pt
python3 -m btb_manager_telegram -l fr

# Make possible to plot the bot's performance in EUR instead of USD
python3 -m btb_manager_telegram -u EUR

# If using other currencies than USD or EUR, for example GBP, you will have to provide
# an openexchangerates API key, see the flag --oer_key.
# Get you key here : https://openexchangerates.org/signup/free
python3 -m btb_manager_telegram -u GBP -o OPENEXCHANGERATES_KEY

# Of course you can combine all of this!
python3 -m btb_manager_telegram -s -l fr -u EUR

# Using nohup with options
nohup python3 -m btb_manager_telegram -s -l fr -u EUR &

# See all available options
python3 -m btb_manager_telegram --help
```

## Stopping the bot
If the trade bot has been launched with the telegram bot, stopping the telegram bot will stop the trade bot.

- If the telegram bot has been launched **without** `nohup`, closing the terminal or pressing `CTRL + C` will stop the bot.

- If the telegram bot has been launched **with** `nohup`, the bot can be stopped with the command `kill $(cat btbmt.pid)` (no animal will be hurt in this operation). If this command respond the file `btbmt.pid`, it his very likely the telegram bot is no longer running.

## Manual upgrade
First of, stop the telegram bot.
```console
git pull
python3 -m pip install --upgrade -r requirements.txt
```
You can now reboot the telegram bot.

## Additional notes

### Custom scripts
This bot supports custom scripts in a plugin manner. An extensive documentation on customs scripts is available [here](./docs/custom-scripts.md).

### Telegram token and chat_id
Make sure that **Binance Trade Bot**'s `config/apprise.yml` file is correctly setup before running, the telegram manager retreives this file to connect the bot.

If **Binance Trade Bot** and **BTB-Manager-Telegram** were **not** installed in the same parent directory or if `apprise.yml` is not setup or you want to use different `token` and `chat_id` from the ones in the `apprise.yml` file, you can set these two keys with the options `--token` and `--chat_id`

### Virtualenvs
If the Binance Trade Bot has its own python environment, that is not shared with the telegram manager, you have to specify the path of the python binary used by the trade bot with the option `--python_path`. For example, if you created a virtualenv specific to the binance trade bot in the folder `/home/user/trading_bot/binance-trade-bot/venv`, you have to run the telegram bot like so:
```console
python3 -m btb_manager_telegram --python_path /home/user/trading_bot/binance-trade-bot/venv/bin/python
```

### Multiple bots
If you would like to run several **Binance Trade Bot** instances at the same time [click here](./docs/multiple-bots.md).

### Compatibility
This program is fully compatible with **Linux** and **Windows** through **WSL** (*Windows Subsystem for Linux*).  

Severa known problems are present on **native Windows** and will not be asserted.

**MacOS** compatibility is unknown, but supposed to be good ad this system is close to **Linux**.

## Screenshots
<details><summary>Click here</summary>

<p align="center">
  	<img height="20%" width="20%" src="https://i.imgur.com/9JUN2G7.jpg" />&nbsp;&nbsp;&nbsp;&nbsp;
    <img height="20%" width="20%" src="https://i.imgur.com/FBSNURs.jpg" />&nbsp;&nbsp;&nbsp;&nbsp;
    <img height="20%" width="20%" src="https://i.imgur.com/UKyREe9.jpg" />
</p>
</details>

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

**If you plan to use real money, USE AT YOUR OWN RISK.**

Under no circumstances will I or the project's maintainers be held responsible or liable in any way for any claims, damages, losses, expenses, costs, or liabilities whatsoever, including, without limitation, any direct or indirect damages for loss of profits.

## Contributors ✨

Many people contributed to the project by providing ideas, finding bugs and helping in the development ([Emoji Key ✨](https://allcontributors.org/docs/en/emoji-key)).  
This project follows the [all-contributors] specification.

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://lorcalhost.com"><img src="https://avatars.githubusercontent.com/u/9640455?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Lorenzo Callegari 乐子睿</b></sub></a><br /><a href="#infra-lorcalhost" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=lorcalhost" title="Tests">⚠️</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=lorcalhost" title="Code">💻</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=lorcalhost" title="Documentation">📖</a> <a href="#maintenance-lorcalhost" title="Maintenance">🚧</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/issues?q=author%3Alorcalhost" title="Bug reports">🐛</a> <a href="#ideas-lorcalhost" title="Ideas, Planning, & Feedback">🤔</a></td>
    <td align="center"><a href="https://DmytroLitvinov.com"><img src="https://avatars.githubusercontent.com/u/16066485?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Dmytro Litvinov</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=DmytroLitvinov" title="Code">💻</a> <a href="#ideas-DmytroLitvinov" title="Ideas, Planning, & Feedback">🤔</a> <a href="#maintenance-DmytroLitvinov" title="Maintenance">🚧</a> <a href="#mentoring-DmytroLitvinov" title="Mentoring">🧑‍🏫</a></td>
    <td align="center"><a href="http://heitorramon.com"><img src="https://avatars.githubusercontent.com/u/1626923?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Heitor Ramon Ribeiro</b></sub></a><br /><a href="#ideas-bloodf" title="Ideas, Planning, & Feedback">🤔</a> <a href="#design-bloodf" title="Design">🎨</a></td>
    <td align="center"><a href="https://github.com/NovusEdge"><img src="https://avatars.githubusercontent.com/u/68768969?v=4?s=100" width="100px;" alt=""/><br /><sub><b>NovusEdge</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=NovusEdge" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/pwnfoo"><img src="https://avatars.githubusercontent.com/u/9546091?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Sachin S. Kamath</b></sub></a><br /><a href="#ideas-pwnfoo" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=pwnfoo" title="Documentation">📖</a></td>
    <td align="center"><a href="https://github.com/kydrenw"><img src="https://avatars.githubusercontent.com/u/4505155?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Hoang Dinh</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/issues?q=author%3Akydrenw" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/idkravitz"><img src="https://avatars.githubusercontent.com/u/200144?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Dmitry Kravtsov</b></sub></a><br /><a href="#ideas-idkravitz" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=idkravitz" title="Code">💻</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/sydekumf"><img src="https://avatars.githubusercontent.com/u/3983052?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Florian Sydekum</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=sydekumf" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/tntwist"><img src="https://avatars.githubusercontent.com/u/6589385?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Nico L.</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/issues?q=author%3Atntwist" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/SeriousSeal"><img src="https://avatars.githubusercontent.com/u/57253532?v=4?s=100" width="100px;" alt=""/><br /><sub><b>SeriousSeal</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=SeriousSeal" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/titulebolide"><img src="https://avatars.githubusercontent.com/u/44905741?v=4?s=100" width="100px;" alt=""/><br /><sub><b>titulebolide</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=titulebolide" title="Documentation">📖</a> <a href="#maintenance-titulebolide" title="Maintenance">🚧</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/pulls?q=is%3Apr+reviewed-by%3Atitulebolide" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/issues?q=author%3Atitulebolide" title="Bug reports">🐛</a> <a href="#translation-titulebolide" title="Translation">🌍</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=titulebolide" title="Tests">⚠️</a> <a href="#tool-titulebolide" title="Tools">🔧</a></td>
    <td align="center"><a href="https://github.com/stgo-eo"><img src="https://avatars.githubusercontent.com/u/7523722?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Stephen Goult</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/issues?q=author%3Astgo-eo" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/Lisiadito"><img src="https://avatars.githubusercontent.com/u/13214912?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Patrick Weingärtner</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=Lisiadito" title="Code">💻</a> <a href="#ideas-Lisiadito" title="Ideas, Planning, & Feedback">🤔</a> <a href="#translation-Lisiadito" title="Translation">🌍</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=Lisiadito" title="Documentation">📖</a></td>
    <td align="center"><a href="https://github.com/FedeArre"><img src="https://avatars.githubusercontent.com/u/39017587?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Federico Arredondo</b></sub></a><br /><a href="#translation-FedeArre" title="Translation">🌍</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/MasaiasuOse"><img src="https://avatars.githubusercontent.com/u/45827629?v=4?s=100" width="100px;" alt=""/><br /><sub><b>MasaiasuOse</b></sub></a><br /><a href="#translation-MasaiasuOse" title="Translation">🌍</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=MasaiasuOse" title="Documentation">📖</a></td>
    <td align="center"><a href="https://github.com/phoenix-blue"><img src="https://avatars.githubusercontent.com/u/13711891?v=4?s=100" width="100px;" alt=""/><br /><sub><b>phoenix-blue</b></sub></a><br /><a href="#translation-phoenix-blue" title="Translation">🌍</a></td>
    <td align="center"><a href="https://github.com/neuhausj"><img src="https://avatars.githubusercontent.com/u/182152?v=4?s=100" width="100px;" alt=""/><br /><sub><b>neuhausj</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=neuhausj" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/santiagocarod"><img src="https://avatars.githubusercontent.com/u/23182382?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Santiago Caro Duque</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/issues?q=author%3Asantiagocarod" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/shhhmel"><img src="https://avatars.githubusercontent.com/u/17930913?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Ivan Myronov</b></sub></a><br /><a href="#translation-shhhmel" title="Translation">🌍</a></td>
    <td align="center"><a href="https://github.com/hieu0nguyen"><img src="https://avatars.githubusercontent.com/u/4257715?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Hieu Nguyen</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/issues?q=author%3Ahieu0nguyen" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/SunBooster"><img src="https://avatars.githubusercontent.com/u/79193009?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Riza Abdul Aziz</b></sub></a><br /><a href="#translation-SunBooster" title="Translation">🌍</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://webdriver.agency/"><img src="https://avatars.githubusercontent.com/u/33579804?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Kelecheck</b></sub></a><br /><a href="#translation-kelecheck" title="Translation">🌍</a></td>
    <td align="center"><a href="http://quentinluppo.fr"><img src="https://avatars.githubusercontent.com/u/34373024?v=4?s=100" width="100px;" alt=""/><br /><sub><b>kentuki</b></sub></a><br /><a href="#translation-QuentinLuppo" title="Translation">🌍</a></td>
    <td align="center"><a href="https://github.com/maromalo"><img src="https://avatars.githubusercontent.com/u/54760464?v=4?s=100" width="100px;" alt=""/><br /><sub><b>maromalo</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/issues?q=author%3Amaromalo" title="Bug reports">🐛</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=maromalo" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/ullasbharadwaj"><img src="https://avatars.githubusercontent.com/u/34948688?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Ulllas Bharadwaj</b></sub></a><br /><a href="#ideas-ullasbharadwaj" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=ullasbharadwaj" title="Code">💻</a> <a href="https://github.com/lorcalhost/BTB-manager-telegram/issues?q=author%3Aullasbharadwaj" title="Bug reports">🐛</a></td>
    <td align="center"><a href="https://github.com/renkasiyas"><img src="https://avatars.githubusercontent.com/u/7783256?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Ren Kasiyas</b></sub></a><br /><a href="#translation-renkasiyas" title="Translation">🌍</a></td>
    <td align="center"><a href="https://github.com/KevinTroyT"><img src="https://avatars.githubusercontent.com/u/35399999?v=4?s=100" width="100px;" alt=""/><br /><sub><b>KevinTroyT</b></sub></a><br /><a href="#translation-KevinTroyT" title="Translation">🌍</a></td>
    <td align="center"><a href="https://github.com/TSecretT"><img src="https://avatars.githubusercontent.com/u/36734601?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Timur</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=TSecretT" title="Code">💻</a> <a href="#translation-TSecretT" title="Translation">🌍</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://links.diogomarques.dev/"><img src="https://avatars.githubusercontent.com/u/52538977?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Diogo Marques</b></sub></a><br /><a href="#translation-DiogoMarques2003" title="Translation">🌍</a></td>
    <td align="center"><a href="https://github.com/stavsher"><img src="https://avatars.githubusercontent.com/u/33731979?v=4?s=100" width="100px;" alt=""/><br /><sub><b>stavsher</b></sub></a><br /><a href="https://github.com/lorcalhost/BTB-manager-telegram/commits?author=stavsher" title="Code">💻</a></td>
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
