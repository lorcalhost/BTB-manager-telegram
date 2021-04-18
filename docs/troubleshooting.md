# Troubleshooting

## 1. I am sending the `/start` command to the bot but it's not answering:

Usually when this happens it means that you haven't properly setup your `apprise.yml` file.  
For security reasons the bot is programmed so that it only responds to people in the chat with `chat_id` equal to the one set in the Telegram URL inside the `apprise.yml` file.

Example of `apprise.yml` file:

```yaml
version: 1
urls:
  - tgram://123456789:AABx8iXjE5C-vG4SDhf6ARgdFgxYxhuHb4A/606743502
```

In this URL:

- `123456789:AABx8iXjE5C-vG4SDhf6ARgdFgxYxhuHb4A` is the bot's `token`
- `606743502` is the `chat_id`

If you are in a one on one chat with the bot you can find your `chat_id` by sending a Telegram message to [@userinfobot](https://t.me/userinfobot).

Note:  
If the bot is not responsive after using the _Update Telegram Bot_ function something may have gone wrong and you need to manually restart _BTB Manager Telegram_.

## 2. ERROR: `Make sure that only one bot instance is running`:

This means that there are two or more instances of `BTB-Manager-Telegram` running at the same time on the same Telegram `token`.  
To fix this error you can kill all `BTB-Manager-Telegram` instances and restart the Telegram bot.  
You can kill the processes using the following command:

```bash
kill -9 $(ps ax | grep btb_manager_telegram | fgrep -v grep | awk '{ print $1 }')
```
