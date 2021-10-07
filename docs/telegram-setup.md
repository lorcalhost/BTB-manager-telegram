# Telegram bot setup guide

_Binance Trade Bot_'s `apprise.yml` file needs to be correctly set up in order for _Binance Trade Bot Manager Telegram_ to work.

1. Create an `apprise.yml` file inside _Binance Trade Bot_'s `config` directory.

2. Copy the contents of `apprise_example.yml` into it.

3. On Telegram, talk to [@botfather] and create a bot.  
   It will send you your Telegram bot `token`.

4. On Telegram, talk to [@userinfobot].  
   It will send you some information among which your Telegram `chat_id`.

5. Inside your `apprise.yml` file delete the `#` character from the `# - tgram://TOKEN/CHAT_ID` line.  
   Replace `TOKEN` and `CHAT_ID` with your `token` and `chat_id`.

After these steps if your token was `123:abc` and your `chat_id` was `1337` your `apprise.yml` file should look like this:

```yaml
version: 1
urls:
  - tgram://123:abc/1337
```

Note:  
_Binance Trade Bot Manager Telegram_ also supports usage of a group chat id instead of a personal `chat_id`.

[@botfather]: https://t.me/botfather
[@userinfobot]: https://t.me/userinfobot
