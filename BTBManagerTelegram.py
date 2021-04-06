# -*- coding: utf-8 -*-
import os

os.chdir(os.path.dirname(os.path.realpath(__file__)))
import argparse
import logging
import sched
import sqlite3
import subprocess
import time
from configparser import ConfigParser
from datetime import datetime
from shutil import copyfile

import psutil
import yaml
from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

MENU, EDIT_COIN_LIST, EDIT_USER_CONFIG, DELETE_DB, UPDATE_TG, UPDATE_BTB = range(6)


class BTBManagerTelegram:
    def __init__(self, root_path=None, token=None, user_id=None):
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        self.logger = logging.getLogger("btb_manager_telegram_logger")

        if root_path is None:
            self.logger.info("No root_path was specified.\nAborting.")
            exit(-1)
        else:
            self.root_path = root_path if root_path[-1] == "/" else (root_path + "/")

        if token is None or user_id is None:
            self.logger.info(
                "Retrieving Telegram token and user_id from apprise.yml file."
            )
            self.token, self.user_id = self.__get_token_from_yaml()
            self.logger.info(
                f"Successfully retrieved Telegram configuration. The bot will only respond to user with user_id {self.user_id}"
            )
        else:
            self.token = token
            self.user_id = user_id

        self.bot = Bot(self.token)

        updater = Updater(self.token)
        dispatcher = updater.dispatcher

        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler(
                    "start", self.__start, Filters.user(user_id=eval(self.user_id))
                )
            ],
            states={
                MENU: [
                    MessageHandler(
                        Filters.regex(
                            "^(Begin|💵 Current value|📈 Progress|➗ Current ratios|🔍 Check bot status|⌛ Trade History|🛠 Maintenance|⚙️ Configurations|▶ Start trade bot|⏹ Stop trade bot|📜 Read last log lines|❌ Delete database|⚙ Edit user.cfg|👛 Edit coin list|📤 Export database|Update Telegram Bot|Update Binance Trade Bot|⬅️ Back|Go back|OK|Cancel update|OK 👌)$"
                        ),
                        self.__menu,
                    )
                ],
                EDIT_COIN_LIST: [
                    MessageHandler(Filters.regex("(.*?)"), self.__edit_coin)
                ],
                EDIT_USER_CONFIG: [
                    MessageHandler(Filters.regex("(.*?)"), self.__edit_user_config)
                ],
                DELETE_DB: [
                    MessageHandler(
                        Filters.regex("^(⚠ Confirm|Go back)$"), self.__delete_db
                    )
                ],
                UPDATE_TG: [
                    MessageHandler(
                        Filters.regex("^(Update|Cancel update)$"), self.__update_tg_bot
                    )
                ],
                UPDATE_BTB: [
                    MessageHandler(
                        Filters.regex("^(Update|Cancel update)$"), self.__update_btb
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", self.__cancel)],
            per_user=True,
        )

        dispatcher.add_handler(conv_handler)
        updater.start_polling()

        # Update checker setup
        self.tg_update_broadcasted_before = False
        self.btb_update_broadcasted_before = False
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler.enter(1, 1, self.__update_checker)
        time.sleep(1)  # needed to prevent thrash
        self.scheduler.run(blocking=False)

        updater.idle()

    def __get_token_from_yaml(self):
        telegram_url = None
        yaml_file_path = f"{self.root_path}config/apprise.yml"
        with open(yaml_file_path) as f:
            parsed_urls = yaml.load(f, Loader=yaml.FullLoader)["urls"]
            for url in parsed_urls:
                if url.startswith("tgram"):
                    telegram_url = url.split("//")[1]
        if not telegram_url:
            self.logger.error(
                "ERROR: No telegram configuration was found in your apprise.yml file.\nAborting."
            )
            exit(-1)
        try:
            tok = telegram_url.split("/")[0]
            uid = telegram_url.split("/")[1]
        except:
            self.logger.error(
                "ERROR: No user_id has been set in the yaml configuration, anyone would be able to control your bot.\nAborting."
            )
            exit(-1)
        return tok, uid

    def __update_checker(self):
        self.logger.info("Checking for updates.")

        if not self.tg_update_broadcasted_before:
            if self.is_tg_bot_update_available():
                self.logger.info("BTB Manager Telegram update found.")

                message = "⚠ An update for _BTB Manager Telegram_ is available\.\n\nPlease update by going to *🛠 Maintenance* and pressing the *Update Telegram Bot* button\."
                self.tg_update_broadcasted_before = True
                self.bot.send_message(self.user_id, message, parse_mode="MarkdownV2")
                self.scheduler.enter(
                    60 * 60 * 12,
                    1,
                    self.__update_reminder,
                    ("_*Reminder*_:\n\n" + message,),
                )

        if not self.btb_update_broadcasted_before:
            if self.is_btb_bot_update_available():
                self.logger.info("Binance Trade Bot update found.")

                message = "⚠ An update for _Binance Trade Bot_ is available\.\n\nPlease update by going to *🛠 Maintenance* and pressing the *Update Binance Trade Bot* button\."
                self.btb_update_broadcasted_before = True
                self.bot.send_message(self.user_id, message, parse_mode="MarkdownV2")
                self.scheduler.enter(
                    60 * 60 * 12,
                    1,
                    self.__update_reminder,
                    ("_*Reminder*_:\n\n" + message,),
                )

        if (
            self.tg_update_broadcasted_before is False
            or self.btb_update_broadcasted_before is False
        ):
            self.scheduler.enter(
                60 * 60,
                1,
                self.__update_checker,
            )

    def __update_reminder(self, message):
        self.logger.info(f"Reminding user: {message}")

        self.bot.send_message(self.user_id, message, parse_mode="MarkdownV2")
        self.scheduler.enter(
            60 * 60 * 12,
            1,
            self.__update_reminder,
        )

    def is_tg_bot_update_available(self):
        try:
            p = subprocess.Popen(
                ["bash", "-c", "git remote update && git status -uno"],
                stdout=subprocess.PIPE,
            )
            output, _ = p.communicate()
            re = "Your branch is behind" in str(output)
        except:
            re = None
        return re

    def is_btb_bot_update_available(self):
        try:
            p = subprocess.Popen(
                [
                    "bash",
                    "-c",
                    "cd ../binance-trade-bot && git remote update && git status -uno",
                ],
                stdout=subprocess.PIPE,
            )
            output, _ = p.communicate()
            re = "Your branch is behind" in str(output)
        except:
            re = None
        return re

    def __start(self, update: Update, _: CallbackContext) -> int:
        self.logger.info("Started conversation.")

        keyboard = [["Begin"]]
        message = f"Hi *{update.message.from_user.first_name}*\!\nWelcome to _Binace Trade Bot Manager Telegram_\.\n\nThis Telegram bot was developed by @lorcalhost\.\nFind out more about the project [here](https://github.com/lorcalhost/BTB-manager-telegram)\.\n\nIf you like the bot please [consider supporting the project 🍻](https://www.buymeacoffee.com/lorcalhost)\."
        reply_markup = ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
        )
        return MENU

    def __menu(self, update: Update, _: CallbackContext) -> int:
        self.logger.info(f"Menu selector. ({update.message.text})")

        keyboard = [
            ["💵 Current value"],
            ["📈 Progress", "➗ Current ratios"],
            ["🔍 Check bot status", "⌛ Trade History"],
            ["🛠 Maintenance", "⚙️ Configurations"],
        ]

        config_keyboard = [
            ["▶ Start trade bot", "⏹ Stop trade bot"],
            ["📜 Read last log lines", "❌ Delete database"],
            ["⚙ Edit user.cfg", "👛 Edit coin list"],
            ["📤 Export database", "⬅️ Back"],
        ]

        maintenance_keyboard = [
            ["Update Telegram Bot"],
            ["Update Binance Trade Bot"],
            ["⬅️ Back"],
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        reply_markup_config = ReplyKeyboardMarkup(config_keyboard, resize_keyboard=True)

        reply_markup_maintenance = ReplyKeyboardMarkup(
            maintenance_keyboard, resize_keyboard=True
        )

        if update.message.text in ["Begin", "⬅️ Back"]:
            message = "Please select one of the options."
            update.message.reply_text(message, reply_markup=reply_markup)

        elif update.message.text in ["Go back", "OK", "⚙️ Configurations"]:
            message = "Please select one of the options."
            update.message.reply_text(message, reply_markup=reply_markup_config)

        elif update.message.text in ["🛠 Maintenance", "Cancel update", "OK 👌"]:
            message = "Please select one of the options."
            update.message.reply_text(message, reply_markup=reply_markup_maintenance)

        elif update.message.text == "💵 Current value":
            for m in self.__btn_current_value():
                update.message.reply_text(
                    m, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )

        elif update.message.text == "📈 Progress":
            for m in self.__btn_check_progress():
                update.message.reply_text(
                    m, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )

        elif update.message.text == "➗ Current ratios":
            for m in self.__btn_current_ratios():
                update.message.reply_text(
                    m, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )

        elif update.message.text == "🔍 Check bot status":
            update.message.reply_text(
                self.__btn_check_status(), reply_markup=reply_markup
            )

        elif update.message.text == "⌛ Trade History":
            for m in self.__btn_trade_history():
                update.message.reply_text(
                    m, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )

        elif update.message.text == "▶ Start trade bot":
            update.message.reply_text(
                self.__btn_start_bot(),
                reply_markup=reply_markup_config,
                parse_mode="MarkdownV2",
            )

        elif update.message.text == "⏹ Stop trade bot":
            update.message.reply_text(
                self.__btn_stop_bot(), reply_markup=reply_markup_config
            )

        elif update.message.text == "📜 Read last log lines":
            update.message.reply_text(
                self.__btn_read_log(),
                reply_markup=reply_markup_config,
                parse_mode="MarkdownV2",
            )

        elif update.message.text == "❌ Delete database":
            re = self.__btn_delete_db()
            if re[1]:
                kb = [["⚠ Confirm", "Go back"]]
                update.message.reply_text(
                    re[0],
                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                    parse_mode="MarkdownV2",
                )
                return DELETE_DB
            else:
                update.message.reply_text(
                    re[0], reply_markup=reply_markup_config, parse_mode="MarkdownV2"
                )

        elif update.message.text == "⚙ Edit user.cfg":
            re = self.__btn_edit_user_cfg()
            if re[1]:
                update.message.reply_text(
                    re[0], reply_markup=ReplyKeyboardRemove(), parse_mode="MarkdownV2"
                )
                return EDIT_USER_CONFIG
            else:
                update.message.reply_text(
                    re[0], reply_markup=reply_markup_config, parse_mode="MarkdownV2"
                )

        elif update.message.text == "👛 Edit coin list":
            re = self.__btn_edit_coin()
            if re[1]:
                update.message.reply_text(
                    re[0], reply_markup=ReplyKeyboardRemove(), parse_mode="MarkdownV2"
                )
                return EDIT_COIN_LIST
            else:
                update.message.reply_text(
                    re[0], reply_markup=reply_markup_config, parse_mode="MarkdownV2"
                )

        elif update.message.text == "📤 Export database":
            re = self.__btn_export_db()
            update.message.reply_text(
                re[0], reply_markup=reply_markup_config, parse_mode="MarkdownV2"
            )
            if re[1] is not None:
                self.bot.send_document(
                    chat_id=update.message.chat_id,
                    document=re[1],
                    filename="crypto_trading.db",
                )

        elif update.message.text == "Update Telegram Bot":
            re = self.__btn_update_tg_bot()
            if re[1]:
                kb = [["Update", "Cancel update"]]
                update.message.reply_text(
                    re[0],
                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                    parse_mode="MarkdownV2",
                )
                return UPDATE_TG
            else:
                update.message.reply_text(
                    re[0],
                    reply_markup=reply_markup_maintenance,
                    parse_mode="MarkdownV2",
                )

        elif update.message.text == "Update Binance Trade Bot":
            re = self.__btn_update_btb()
            if re[1]:
                kb = [["Update", "Cancel update"]]
                update.message.reply_text(
                    re[0],
                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                    parse_mode="MarkdownV2",
                )
                return UPDATE_BTB
            else:
                update.message.reply_text(
                    re[0],
                    reply_markup=reply_markup_maintenance,
                    parse_mode="MarkdownV2",
                )

        return MENU

    def __edit_user_config(self, update: Update, _: CallbackContext) -> int:
        self.logger.info(f"Editing user configuration. ({update.message.text})")

        if update.message.text != "/stop":
            message = f"✔ Successfully edited user configuration file to:\n\n```\n{update.message.text}\n```".replace(
                ".", "\."
            )
            user_cfg_file_path = f"{self.root_path}user.cfg"
            try:
                copyfile(user_cfg_file_path, f"{user_cfg_file_path}.backup")
                with open(user_cfg_file_path, "w") as f:
                    f.write(update.message.text + "\n\n\n")
            except:
                message = "❌ Unable to edit user configuration file\."
        else:
            message = (
                "👌 Exited without changes\.\nYour `user.cfg` file was *not* modified\."
            )

        keyboard = [["Go back"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

        return MENU

    def __edit_coin(self, update: Update, _: CallbackContext) -> int:
        self.logger.info(f"Editing coin list. ({update.message.text})")

        if update.message.text != "/stop":
            message = f"✔ Successfully edited coin list file to:\n\n```\n{update.message.text}\n```".replace(
                ".", "\."
            )
            coin_file_path = f"{self.root_path}supported_coin_list"
            try:
                copyfile(coin_file_path, f"{coin_file_path}.backup")
                with open(coin_file_path, "w") as f:
                    f.write(update.message.text + "\n")
            except:
                message = "❌ Unable to edit coin list file\."
        else:
            message = "👌 Exited without changes\.\nYour `supported_coin_list` file was *not* modified\."

        keyboard = [["Go back"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

        return MENU

    def __delete_db(self, update: Update, _: CallbackContext) -> int:
        self.logger.info(
            f"Asking if the user really wants to delete the db. ({update.message.text})"
        )

        if update.message.text != "Go back":
            message = "✔ Successfully deleted database file\."
            db_file_path = f"{self.root_path}data/crypto_trading.db"
            try:
                copyfile(db_file_path, f"{db_file_path}.backup")
                os.remove(db_file_path)
            except:
                message = "❌ Unable to delete database file\."
        else:
            message = "👌 Exited without changes\.\nYour database was *not* deleted\."

        keyboard = [["OK"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

        return MENU

    def __update_tg_bot(self, update: Update, _: CallbackContext) -> int:
        self.logger.info(f"Updating BTB Manager Telegram. ({update.message.text})")

        if update.message.text != "Cancel update":
            message = "The bot is updating\.\nWait a few seconds then start the bot again with /start"
            keyboard = [["/start"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            update.message.reply_text(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
            try:
                subprocess.call(
                    "kill -9 $(ps ax | grep BTBManagerTelegram | fgrep -v grep | awk '{ print $1 }') && git pull && $(which python3) -m pip install -r requirements.txt && $(which python3) BTBManagerTelegram.py &",
                    shell=True,
                )
            except:
                message = "Unable to update BTB Manager Telegram"
                update.message.reply_text(
                    message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
        else:
            message = (
                "👌 Exited without changes\.\nBTB Manager Telegram was *not* updated\."
            )
            keyboard = [["OK 👌"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            update.message.reply_text(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

        return MENU

    def __update_btb(self, update: Update, _: CallbackContext) -> int:
        self.logger.info(f"Updating Binance Trade Bot. ({update.message.text})")

        keyboard = [["OK 👌"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        if update.message.text != "Cancel update":
            message = "The bot is updating\.\nWait a few seconds, the bot will restart automatically\."
            update.message.reply_text(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
            try:
                self.__find_and_kill_process()
                subprocess.call(
                    f"cd {self.root_path} && git pull && $(which python3) -m pip install -r requirements.txt && $(which python3) -m binance_trade_bot &",
                    shell=True,
                )
            except:
                message = "Unable to update Binance Trade Bot"
                update.message.reply_text(
                    message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
        else:
            message = (
                "👌 Exited without changes\.\nBinance Trade Bot was *not* updated\."
            )
            update.message.reply_text(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

        return MENU

    @staticmethod
    def __find_process():
        for p in psutil.process_iter():
            if "binance_trade_bot" in p.name() or "binance_trade_bot" in " ".join(
                p.cmdline()
            ):
                return True
        return False

    def __find_and_kill_process(self):
        try:
            for p in psutil.process_iter():
                if "binance_trade_bot" in p.name() or "binance_trade_bot" in " ".join(
                    p.cmdline()
                ):
                    p.terminate()
                    p.wait()
        except Exception as e:
            self.logger.info(f"ERROR: {e}")

    @staticmethod
    def __4096_cutter(m_list):
        message = [""]
        index = 0
        for m in m_list:
            if len(message[index]) + len(m) <= 4096:
                message[index] += m
            else:
                message.append(m)
                index += 1
        return message

    # BUTTONS
    def __btn_current_value(self):
        self.logger.info("Current value button pressed.")

        db_file_path = f"{self.root_path}data/crypto_trading.db"
        message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
        if os.path.exists(db_file_path):
            try:
                con = sqlite3.connect(db_file_path)
                cur = con.cursor()

                # Get current coin symbol, bridge symbol, order state, order size, initial buying price
                try:
                    cur.execute(
                        """SELECT alt_coin_id, crypto_coin_id, state, crypto_starting_balance, crypto_trade_amount FROM trade_history ORDER BY datetime DESC LIMIT 1;"""
                    )
                    current_coin, bridge, state, order_size, buy_price = cur.fetchone()
                    if current_coin is None:
                        raise Exception()
                    if state == "ORDERED":
                        return [
                            f"A buy order of `{round(order_size, 2)}` *{bridge}* is currently placed on coin *{current_coin}*.\n\n_Waiting for buy order to complete_.".replace(
                                ".", "\."
                            )
                        ]
                except:
                    con.close()
                    return [f"❌ Unable to fetch current coin from database\."]

                # Get balance, current coin price in USD, current coin price in BTC
                try:
                    cur.execute(
                        f"""SELECT balance, usd_price, btc_price, datetime FROM 'coin_value' WHERE coin_id = '{current_coin}' ORDER BY datetime DESC LIMIT 1;"""
                    )
                    query = cur.fetchone()
                    if query is None:
                        return [
                            f"❌ No information about *{current_coin}* available in the database\.",
                            f"⚠ If you tried using the `Current value` button during a trade please try again after the trade has been completed\.",
                        ]
                    balance, usd_price, btc_price, last_update = query
                    if balance is None:
                        balance = 0
                    if usd_price is None:
                        usd_price = 0
                    if btc_price is None:
                        btc_price = 0
                    last_update = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S.%f")
                except:
                    con.close()
                    return [
                        f"❌ Unable to fetch current coin information from database\.",
                        f"⚠ If you tried using the `Current value` button during a trade please try again after the trade has been completed\.",
                    ]

                # Generate message
                try:
                    m_list = [
                        f'\nLast update: `{last_update.strftime("%H:%M:%S %d/%m/%Y")}`\n\n*Current coin {current_coin}:*\n\t\- Balance: `{round(balance, 6)}` *{current_coin}*\n\t\- Current coin exchange ratio: `{round((buy_price / balance), 6)}` *{bridge}/{current_coin}*\n\t\- Current coin price: `{round(usd_price, 2)}` *USD/{bridge}*\n\t\- Value in *USD*: `{round((balance * usd_price), 2)}` *USD*\n\t\- Value in *BTC*: `{round((balance * btc_price), 6)}` *BTC*\n\n\t_Initially bought for_ {round(buy_price, 2)} *{bridge}* (`{round((buy_price / balance), 6)}` *{bridge}/{current_coin}*)\n'.replace(
                            ".", "\."
                        )
                    ]
                    message = self.__4096_cutter(m_list)
                    con.close()
                except:
                    con.close()
                    return [
                        f"❌ Something went wrong, unable to generate value at this time\."
                    ]
            except:
                message = ["❌ Unable to perform actions on the database\."]
        return message

    def __btn_check_progress(self):
        self.logger.info("Progress button pressed.")

        db_file_path = f"{self.root_path}data/crypto_trading.db"
        user_cfg_file_path = f"{self.root_path}user.cfg"
        message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
        if os.path.exists(db_file_path):
            try:
                con = sqlite3.connect(db_file_path)
                cur = con.cursor()

                # Get progress information
                try:
                    cur.execute(
                        """SELECT th1.alt_coin_id AS coin, th1.alt_trade_amount AS amount, th1.crypto_trade_amount AS priceInUSD,(th1.alt_trade_amount - ( SELECT th2.alt_trade_amount FROM trade_history th2 WHERE th2.alt_coin_id = th1.alt_coin_id AND th1.datetime > th2.datetime AND th2.selling = 0 ORDER BY th2.datetime DESC LIMIT 1)) AS change, datetime FROM trade_history th1 WHERE th1.state = 'COMPLETE' AND th1.selling = 0 ORDER BY th1.datetime DESC LIMIT 15"""
                    )
                    query = cur.fetchall()

                    # Generate message
                    m_list = [f"Current coin amount progress:\n\n"]
                    for coin in query:
                        last_trade_date = datetime.strptime(
                            coin[4], "%Y-%m-%d %H:%M:%S.%f"
                        ).strftime("%H:%M:%S %d/%m/%Y")
                        m_list.append(
                            f'*{coin[0]}*\n\t\- Amount: `{round(coin[1], 6)}` *{coin[0]}*\n\t\- Price: `{round(coin[2], 2)}` *USD*\n\t\- Change: {f"`{round(coin[3], 2)}` *{coin[0]}*" if coin[3] is not None else f"`{coin[3]}`"}\n\t\- Last trade: `{last_trade_date}`\n\n'.replace(
                                ".", "\."
                            )
                        )

                    message = self.__4096_cutter(m_list)
                    con.close()
                except:
                    con.close()
                    return [f"❌ Unable to fetch progress information from database\."]
            except:
                message = ["❌ Unable to perform actions on the database\."]
        return message

    def __btn_current_ratios(self):
        self.logger.info("Current ratios button pressed.")

        db_file_path = f"{self.root_path}data/crypto_trading.db"
        user_cfg_file_path = f"{self.root_path}user.cfg"
        message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
        if os.path.exists(db_file_path):
            try:
                # Get bridge currency symbol
                with open(user_cfg_file_path) as cfg:
                    config = ConfigParser()
                    config.read_file(cfg)
                    bridge = config.get("binance_user_config", "bridge")

                con = sqlite3.connect(db_file_path)
                cur = con.cursor()

                # Get current coin symbol
                try:
                    cur.execute(
                        """SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1;"""
                    )
                    current_coin = cur.fetchone()[0]
                    if current_coin is None:
                        raise Exception()
                except:
                    con.close()
                    return [f"❌ Unable to fetch current coin from database\."]

                # Get prices and ratios of all alt coins
                try:
                    cur.execute(
                        f"""SELECT sh.datetime, p.to_coin_id, sh.other_coin_price, ( ( ( current_coin_price / other_coin_price ) - 0.001 * 5 * ( current_coin_price / other_coin_price ) ) - sh.target_ratio ) AS 'ratio_dict' FROM scout_history sh JOIN pairs p ON p.id = sh.pair_id WHERE p.from_coin_id='{current_coin}' AND p.from_coin_id = ( SELECT alt_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1) ORDER BY sh.datetime DESC LIMIT ( SELECT count(DISTINCT pairs.to_coin_id) FROM pairs WHERE pairs.from_coin_id='{current_coin}');"""
                    )
                    query = cur.fetchall()

                    # Generate message
                    last_update = datetime.strptime(query[0][0], "%Y-%m-%d %H:%M:%S.%f")
                    query = sorted(query, key=lambda k: k[-1], reverse=True)

                    m_list = [
                        f'\nLast update: `{last_update.strftime("%H:%M:%S %d/%m/%Y")}`\n\n*Coin ratios compared to {current_coin}:*\n'.replace(
                            ".", "\."
                        )
                    ]
                    for coin in query:
                        m_list.append(
                            f"*{coin[1]}*:\n\t\- Price: `{coin[2]}` *{bridge}*\n\t\- Ratio: `{round(coin[3], 6)}`\n\n".replace(
                                ".", "\."
                            )
                        )

                    message = self.__4096_cutter(m_list)
                    con.close()
                except:
                    con.close()
                    return [
                        f"❌ Something went wrong, unable to generate ratios at this time\."
                    ]
            except:
                message = ["❌ Unable to perform actions on the database\."]
        return message

    def __btn_check_status(self):
        self.logger.info("Check status button pressed.")

        message = "⚠ Binance Trade Bot is not running."
        if self.__find_process():
            message = "✔ Binance Trade Bot is running."
        return message

    def __btn_trade_history(self):
        self.logger.info("Trade history button pressed.")

        db_file_path = f"{self.root_path}data/crypto_trading.db"
        message = [f"⚠ Unable to find database file at `{db_file_path}`\."]
        if os.path.exists(db_file_path):
            try:
                con = sqlite3.connect(db_file_path)
                cur = con.cursor()

                # Get last 10 trades
                try:
                    cur.execute(
                        """SELECT alt_coin_id, crypto_coin_id, selling, state, alt_trade_amount, crypto_trade_amount, datetime FROM trade_history ORDER BY datetime DESC LIMIT 10;"""
                    )
                    query = cur.fetchall()

                    m_list = [
                        f"Last **{10 if len(query) > 10 else len(query)}** trades:\n\n"
                    ]
                    for trade in query:
                        d = datetime.strptime(trade[6], "%Y-%m-%d %H:%M:%S.%f")
                        m = f'`{d.strftime("%H:%M:%S %d/%m/%Y")}`\n*{"Sold" if trade[2] else "Bought"}* `{round(trade[4], 6)}` *{trade[0]}*{f" for `{round(trade[5], 2)}` *{trade[1]}*" if trade[5] is not None else ""}\nStatus: _*{trade[3]}*_\n\n'
                        m_list.append(m.replace(".", "\."))

                    message = self.__4096_cutter(m_list)
                    con.close()
                except:
                    con.close()
                    return [
                        f"❌ Something went wrong, unable to generate trade history at this time\."
                    ]
            except:
                message = ["❌ Unable to perform actions on the database\."]
        return message

    def __btn_start_bot(self):
        self.logger.info("Start bot button pressed.")

        message = "⚠ Binance Trade Bot is already running\."
        if not self.__find_process():
            if os.path.exists(f"{self.root_path}binance_trade_bot/"):
                subprocess.call(
                    f"cd {self.root_path} && $(which python3) -m binance_trade_bot &",
                    shell=True,
                )
                if not self.__find_process():
                    message = "❌ Unable to start Binance Trade Bot\."
                else:
                    message = "✔ Binance Trade Bot successfully started\."
            else:
                message = "❌ Unable to find _Binance Trade Bot_ installation in this directory\.\nMake sure the `BTBManagerTelegram.py` file is in the _Binance Trade Bot_ installation folder\."
        return message

    def __btn_stop_bot(self):
        self.logger.info("Stop bot button pressed.")

        message = "⚠ Binance Trade Bot is not running."
        if self.__find_process():
            self.__find_and_kill_process()
            if not self.__find_process():
                message = "✔ Successfully stopped the bot."
            else:
                message = "❌ Unable to stop Binance Trade Bot.\n\nIf you are running the telegram bot on Windows make sure to run with administrator privileges."
        return message

    def __btn_read_log(self):
        self.logger.info("Read log button pressed.")

        log_file_path = f"{self.root_path}logs/crypto_trading.log"
        message = f"❌ Unable to find log file at `{log_file_path}`.".replace(".", "\.")
        if os.path.exists(log_file_path):
            with open(log_file_path) as f:
                file_content = f.read().replace(".", "\.")[-4000:]
                message = (
                    f"Last *4000* characters in log file:\n\n```\n{file_content}\n```"
                )
        return message

    def __btn_delete_db(self):
        self.logger.info("Delete database button pressed.")

        message = "⚠ Please stop Binance Trade Bot before deleting the database file\."
        delete = False
        db_file_path = f"{self.root_path}data/crypto_trading.db"
        if not self.__find_process():
            if os.path.exists(db_file_path):
                message = "Are you sure you want to delete the database file?"
                delete = True
            else:
                message = (
                    f"⚠ Unable to find database file at `{db_file_path}`.".replace(
                        ".", "\."
                    )
                )
        return [message, delete]

    def __btn_edit_user_cfg(self):
        self.logger.info("Edit user configuration button pressed.")

        message = (
            "⚠ Please stop Binance Trade Bot before editing user configuration file\."
        )
        edit = False
        user_cfg_file_path = f"{self.root_path}user.cfg"
        if not self.__find_process():
            if os.path.exists(user_cfg_file_path):
                with open(user_cfg_file_path) as f:
                    message = f"Current configuration file is:\n\n```\n{f.read()}\n```\n\n_*Please reply with a message containing the updated configuration*_.\n\nWrite /stop to stop editing and exit without changes.".replace(
                        ".", "\."
                    )
                    edit = True
            else:
                message = f"❌ Unable to find user configuration file at `{user_cfg_file_path}`.".replace(
                    ".", "\."
                )
        return [message, edit]

    def __btn_edit_coin(self):
        self.logger.info("Edit coin list button pressed.")

        message = "⚠ Please stop Binance Trade Bot before editing the coin list\."
        edit = False
        coin_file_path = f"{self.root_path}supported_coin_list"
        if not self.__find_process():
            if os.path.exists(coin_file_path):
                with open(coin_file_path) as f:
                    message = f"Current coin list is:\n\n```\n{f.read()}\n```\n\n_*Please reply with a message containing the updated coin list*_.\n\nWrite /stop to stop editing and exit without changes.".replace(
                        ".", "\."
                    )
                    edit = True
            else:
                message = (
                    f"❌ Unable to find coin list file at `{coin_file_path}`.".replace(
                        ".", "\."
                    )
                )
        return [message, edit]

    def __btn_export_db(self):
        self.logger.info("Export database button pressed.")

        message = "⚠ Please stop Binance Trade Bot before exporting the database file\."
        db_file_path = f"{self.root_path}data/crypto_trading.db"
        fil = None
        if not self.__find_process():
            if os.path.exists(db_file_path):
                with open(db_file_path, "rb") as db:
                    fil = db.read()
                message = "Here is your database file:"
            else:
                message = "❌ Unable to Export the database file\."
        return [message, fil]

    def __btn_update_tg_bot(self):
        self.logger.info("Update Telegram bot button pressed.")

        message = "Your BTB Manager Telegram installation is already up to date\."
        upd = False
        to_update = is_tg_bot_update_available()
        if to_update is not None:
            if to_update:
                message = "An update for BTB Manager Telegram is available\.\nWould you like to update now?"
                upd = True
        else:
            message = (
                "Error while trying to fetch BTB Manager Telegram version information\."
            )
        return [message, upd]

    def __btn_update_btb(self):
        self.logger.info("Update Binance Trade Bot button pressed.")

        message = "Your Binance Trade Bot installation is already up to date\."
        upd = False
        to_update = is_btb_bot_update_available()
        if to_update is not None:
            if to_update:
                upd = True
                message = "An update for Binance Trade Bot is available\.\nWould you like to update now?"
        else:
            message = (
                "Error while trying to fetch Binance Trade Bot version information\."
            )
        return [message, upd]

    # STOP CONVERSATION
    def __cancel(self, update: Update, _: CallbackContext) -> int:
        self.logger.info("Conversation canceled.")

        update.message.reply_text(
            "Bye! I hope we can talk again some day.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Thanks for using Binance Trade Bot Manager Telegram. By default the program will use "../binance-trade-bot/" as binance-trade-bot installation path.'
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        help="(optional) binance-trade-bot installation absolute path",
        default="../binance-trade-bot/",
    )
    parser.add_argument(
        "-t", "--token", type=str, help="(optional) Telegram bot token", default=None
    )
    parser.add_argument(
        "-u", "--user_id", type=str, help="(optional) Telegram user id", default=None
    )
    args = parser.parse_args()
    BTBManagerTelegram(root_path=args.path, token=args.token, user_id=args.user_id)
