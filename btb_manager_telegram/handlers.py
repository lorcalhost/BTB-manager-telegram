import json
import os
import shutil
import sqlite3
import subprocess
import sys
from configparser import ConfigParser

from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import escape_markdown

from btb_manager_telegram import (
    BOUGHT,
    BUYING,
    CUSTOM_SCRIPT,
    DELETE_DB,
    EDIT_COIN_LIST,
    EDIT_USER_CONFIG,
    MENU,
    PANIC_BUTTON,
    SELLING,
    SOLD,
    UPDATE_BTB,
    UPDATE_TG,
    buttons,
    logger,
    settings,
)
from btb_manager_telegram.binance_api_utils import send_signed_request
from btb_manager_telegram.utils import (
    find_and_kill_binance_trade_bot_process,
    get_custom_scripts_keyboard,
    kill_btb_manager_telegram_process,
    telegram_text_truncator,
    load_custom_settings
)


def menu(update: Update, _: CallbackContext) -> int:
    logger.info(f"Menu selector. ({update.message.text})")

    # Panic button disabled until PR #74 is complete
    # keyboard = [
    #     ["💵 Current value", "➗ Current ratios"],
    #     ["📈 Progress", "⌛ Trade History"],
    #     ["🔍 Check bot status", "🚨 Panic button"],
    #     ["🛠 Maintenance", "⚙️ Configurations"],
    # ]

    keyboard = [
        ["💵 Current value", "📈 Progress"],
        ["➗ Current ratios", "🔀 Next coin"],
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
        ["⬆ Update Telegram Bot"],
        ["⬆ Update Binance Trade Bot"],
        ["🤖 Execute custom script"],
        ["⬅️ Back"],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    reply_markup_config = ReplyKeyboardMarkup(config_keyboard, resize_keyboard=True)

    reply_markup_maintenance = ReplyKeyboardMarkup(
        maintenance_keyboard, resize_keyboard=True
    )

    if update.message.text in ["Begin", "⬅️ Back", "Great 👌"]:
        message = "Please select one of the options."
        update.message.reply_text(message, reply_markup=reply_markup)

    elif update.message.text in ["Go back", "OK", "⚙️ Configurations"]:
        message = "Please select one of the options."
        update.message.reply_text(message, reply_markup=reply_markup_config)

    elif update.message.text in ["🛠 Maintenance", "Cancel update", "Cancel", "OK 👌"]:
        message = "Please select one of the options."
        update.message.reply_text(message, reply_markup=reply_markup_maintenance)

    elif update.message.text == "💵 Current value":
        for mes in buttons.current_value():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
        try:    
            if load_custom_settings()["Total_Binance_Wallet_Balance"] == True:
                for mes in buttons.wallet_value():
                    update.message.reply_text(
                        mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
                    )
        except:
            print('Setting not found')            
        

    elif update.message.text == "🚨 Panic button":
        message, status = buttons.panic_btn()
        if status in [BOUGHT, BUYING, SOLD, SELLING]:
            if status == BOUGHT:
                kb = [["⚠ Stop & sell at market price"], ["Go back"]]
            elif status in [BUYING, SELLING]:
                kb = [["⚠ Stop & cancel order"], ["Go back"]]
            elif status == SOLD:
                kb = [["⚠ Stop the bot"], ["Go back"]]

            update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return PANIC_BUTTON

        else:
            update.message.reply_text(
                message, reply_markup=reply_markup_config, parse_mode="MarkdownV2"
            )

    elif update.message.text == "📈 Progress":
        for mes in buttons.check_progress():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

    elif update.message.text == "➗ Current ratios":
        for mes in buttons.current_ratios():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

    elif update.message.text == "🔀 Next coin":
        for mes in buttons.next_coin():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

    elif update.message.text == "🔍 Check bot status":
        update.message.reply_text(buttons.check_status(), reply_markup=reply_markup)

    elif update.message.text == "⌛ Trade History":
        for mes in buttons.trade_history():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

    elif update.message.text == "▶ Start trade bot":
        update.message.reply_text(
            buttons.start_bot(),
            reply_markup=reply_markup_config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == "⏹ Stop trade bot":
        update.message.reply_text(buttons.stop_bot(), reply_markup=reply_markup_config)

    elif update.message.text == "📜 Read last log lines":
        update.message.reply_text(
            buttons.read_log(),
            reply_markup=reply_markup_config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == "❌ Delete database":
        message, status = buttons.delete_db()
        if status:
            kb = [["⚠ Confirm", "Go back"]]
            update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return DELETE_DB
        else:
            update.message.reply_text(
                message, reply_markup=reply_markup_config, parse_mode="MarkdownV2"
            )

    elif update.message.text == "⚙ Edit user.cfg":
        message, status = buttons.edit_user_cfg()
        if status:
            update.message.reply_text(
                message, reply_markup=ReplyKeyboardRemove(), parse_mode="MarkdownV2"
            )
            return EDIT_USER_CONFIG
        else:
            update.message.reply_text(
                message, reply_markup=reply_markup_config, parse_mode="MarkdownV2"
            )

    elif update.message.text == "👛 Edit coin list":
        message, status = buttons.edit_coin()
        if status:
            update.message.reply_text(
                message, reply_markup=ReplyKeyboardRemove(), parse_mode="MarkdownV2"
            )
            return EDIT_COIN_LIST
        else:
            update.message.reply_text(
                message, reply_markup=reply_markup_config, parse_mode="MarkdownV2"
            )

    elif update.message.text == "📤 Export database":
        message, document = buttons.export_db()
        update.message.reply_text(
            message, reply_markup=reply_markup_config, parse_mode="MarkdownV2"
        )
        if document is not None:
            bot = Bot(settings.TOKEN)
            bot.send_document(
                chat_id=update.message.chat_id,
                document=document,
                filename="crypto_trading.db",
            )

    elif update.message.text == "⬆ Update Telegram Bot":
        message, status = buttons.update_tg_bot()
        if status:
            kb = [["Update", "Cancel update"]]
            update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return UPDATE_TG
        else:
            update.message.reply_text(
                message,
                reply_markup=reply_markup_maintenance,
                parse_mode="MarkdownV2",
            )

    elif update.message.text == "⬆ Update Binance Trade Bot":
        message, status = buttons.update_btb()
        if status:
            kb = [["Update", "Cancel update"]]
            update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return UPDATE_BTB
        else:
            update.message.reply_text(
                message,
                reply_markup=reply_markup_maintenance,
                parse_mode="MarkdownV2",
            )

    elif update.message.text == "🤖 Execute custom script":
        kb, status, message = get_custom_scripts_keyboard()
        if status:
            update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return CUSTOM_SCRIPT
        else:
            update.message.reply_text(
                message,
                reply_markup=reply_markup_maintenance,
                parse_mode="MarkdownV2",
            )

    return MENU


def start(update: Update, _: CallbackContext) -> int:
    logger.info("Started conversation.")

    keyboard = [["Begin"]]
    message = (
        f"Hi *{escape_markdown(update.message.from_user.first_name, version=2)}*\!\n"
        f"Welcome to _Binace Trade Bot Manager Telegram_\.\n\n"
        f"This Telegram bot was developed by @lorcalhost\.\n"
        f"Find out more about the project [here](https://github.com/lorcalhost/BTB-manager-telegram)\.\n\n"
        f"*If you like my work please [consider supporting the project through a small donation](https://github.com/sponsors/lorcalhost)\. ❤*"
    )
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


def edit_coin(update: Update, _: CallbackContext) -> int:
    logger.info(f"Editing coin list. ({update.message.text})")

    if update.message.text != "/stop":
        message = (
            f"✔ Successfully edited coin list file to:\n\n"
            f"```\n"
            f"{update.message.text}\n"
            f"```".replace(".", "\.")
        )
        coin_file_path = os.path.join(settings.ROOT_PATH, "supported_coin_list")
        try:
            shutil.copyfile(coin_file_path, f"{coin_file_path}.backup")
            with open(coin_file_path, "w") as f:
                f.write(update.message.text + "\n")
        except Exception as e:
            logger.error(f"❌ Unable to edit coin list file: {e}", exc_info=True)
            message = "❌ Unable to edit coin list file\."
    else:
        message = "👌 Exited without changes\.\nYour `supported_coin_list` file was *not* modified\."

    keyboard = [["Go back"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
    )

    return MENU


def edit_user_config(update: Update, _: CallbackContext) -> int:
    logger.info(f"Editing user configuration. ({update.message.text})")

    if update.message.text != "/stop":
        message = (
            f"✔ Successfully edited user configuration file to:\n\n"
            f"```\n"
            f"{update.message.text}\n"
            f"```".replace(".", "\.")
        )
        user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
        try:
            shutil.copyfile(user_cfg_file_path, f"{user_cfg_file_path}.backup")
            with open(user_cfg_file_path, "w") as f:
                f.write(update.message.text + "\n\n\n")
        except Exception as e:
            logger.error(
                f"❌ Unable to edit user configuration file: {e}", exc_info=True
            )
            message = "❌ Unable to edit user configuration file\."
    else:
        message = (
            "👌 Exited without changes\.\n" "Your `user.cfg` file was *not* modified\."
        )

    keyboard = [["Go back"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
    )

    return MENU


def delete_db(update: Update, _: CallbackContext) -> int:
    logger.info(
        f"Asking if the user really wants to delete the db. ({update.message.text})"
    )

    if update.message.text != "Go back":
        message = "✔ Successfully deleted database file\."
        db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
        log_file_path = os.path.join(settings.ROOT_PATH, "logs/crypto_trading.log")
        try:
            shutil.copyfile(db_file_path, f"{db_file_path}.backup")
            os.remove(db_file_path)
        except Exception as e:
            logger.error(f"❌ Unable to delete database file: {e}", exc_info=True)
            message = "❌ Unable to delete database file\."
        try:
            with open(log_file_path, "w") as f:
                f.truncate()
        except Exception as e:
            logger.error(f"❌ Unable to clear log file: {e}", exc_info=True)
            message = "❌ Unable to clear log file\."

    else:
        message = "👌 Exited without changes\.\n" "Your database was *not* deleted\."

    keyboard = [["OK"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
    )

    return MENU


def update_tg_bot(update: Update, _: CallbackContext) -> int:
    logger.info(f"Updating BTB Manager Telegram. ({update.message.text})")

    if update.message.text != "Cancel update":
        message = (
            "The bot is updating\.\n"
            "Wait a few seconds then start the bot again with /start"
        )
        keyboard = [["/start"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )
        try:
            manager_python_path = sys.executable
            subprocess.call(
                f"git pull && {manager_python_path} -m pip install -r requirements.txt --upgrade && "
                f"{manager_python_path} -m btb_manager_telegram {settings.RAW_ARGS} &",
                shell=True,
            )
            kill_btb_manager_telegram_process()
        except Exception as e:
            logger.error(f"❌ Unable to update BTB Manager Telegram: {e}", exc_info=True)
            message = "Unable to update BTB Manager Telegram"
            update.message.reply_text(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
    else:
        message = (
            "👌 Exited without changes\.\n" "BTB Manager Telegram was *not* updated\."
        )
        keyboard = [["OK 👌"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    return MENU


def update_btb(update: Update, _: CallbackContext) -> int:
    logger.info(f"Updating Binance Trade Bot. ({update.message.text})")

    keyboard = [["OK 👌"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    if update.message.text != "Cancel update":
        message = (
            "The bot has been stopped and is now updating\.\n"
            "Wait a few seconds, then restart manually\."
        )
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )
        try:
            find_and_kill_binance_trade_bot_process()
            subprocess.call(
                f"cd {settings.ROOT_PATH} && "
                f"git pull && "
                f"{settings.PYTHON_PATH} -m pip install -r requirements.txt --upgrade",
                shell=True,
            )
            settings.BTB_UPDATE_BROADCASTED_BEFORE = False
        except Exception as e:
            logger.error(f"Unable to update Binance Trade Bot: {e}", exc_info=True)
            message = "Unable to update Binance Trade Bot"
            update.message.reply_text(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
    else:
        message = "👌 Exited without changes\.\n" "Binance Trade Bot was *not* updated\."
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    return MENU


def panic(update: Update, _: CallbackContext) -> int:
    logger.info(f"Panic Button is doing its job. ({update.message.text})")

    keyboard = [["Great 👌"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    if update.message.text != "Go back":
        find_and_kill_binance_trade_bot_process()

        # Get current coin pair
        db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
        con = sqlite3.connect(db_file_path)
        cur = con.cursor()

        # Get last trade
        cur.execute(
            """SELECT alt_coin_id, crypto_coin_id FROM trade_history ORDER BY datetime DESC LIMIT 1;"""
        )
        alt_coin_id, crypto_coin_id = cur.fetchone()

        # Get Binance api keys and tld
        user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
        with open(user_cfg_file_path) as cfg:
            config = ConfigParser()
            config.read_file(cfg)
            api_key = config.get("binance_user_config", "api_key")
            api_secret_key = config.get("binance_user_config", "api_secret_key")
            tld = config.get("binance_user_config", "tld")

        if update.message.text != "⚠ Stop & sell at market price":
            params = {
                "symbol": f"{alt_coin_id}{crypto_coin_id}",
                "side": "SELL",
                "type": "MARKET",
            }
            message = send_signed_request(
                api_key,
                api_secret_key,
                f"https://api.binance.{tld}",
                "POST",
                "/api/v3/order",
                payload=params,
            )

        if update.message.text != "⚠ Stop & cancel order":
            params = {"symbol": f"{alt_coin_id}{crypto_coin_id}"}
            message = send_signed_request(
                api_key,
                api_secret_key,
                f"https://api.binance.{tld}",
                "DELETE",
                "/api/v3/openOrders",
                payload=params,
            )

        if update.message.text != "⚠ Stop the bot":
            message = "Killed _Binance Trade Bot_!"
    else:
        message = "👌 Exited without changes\.\n" "Binance Trade Bot was *not* updated\."

    update.message.reply_text(
        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
    )
    return MENU


def execute_custom_script(update: Update, _: CallbackContext) -> int:
    logger.info(f"Going to 🤖 execute custom script. ({update.message.text})")

    keyboard = [["OK 👌"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    custom_scripts_path = "./config/custom_scripts.json"
    if update.message.text != "Cancel":
        with open(custom_scripts_path) as f:
            scripts = json.load(f)

            try:
                command = ["bash", "-c", str(scripts[update.message.text])]
            except Exception as e:
                logger.error(
                    f"Unable to find script named {update.message.text} in custom_scripts.json file: {e}",
                    exc_info=True,
                )
                message = f"Unable to find script named `{escape_markdown(update.message.text, version=2)}` in `custom_scripts.json` file\."
                update.message.reply_text(
                    message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )

            try:
                proc = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                )
                output, _ = proc.communicate()
                message_list = telegram_text_truncator(
                    escape_markdown(output.decode("utf-8"), version=2),
                    padding_chars_head="```\n",
                    padding_chars_tail="```",
                )
                for message in message_list:
                    update.message.reply_text(
                        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                    )
            except Exception as e:
                logger.error(f"Error during script execution: {e}", exc_info=True)
                message = "Error during script execution\."
                update.message.reply_text(
                    message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )

    return MENU


def cancel(update: Update, _: CallbackContext) -> int:
    logger.info("Conversation canceled.")

    update.message.reply_text(
        "Bye! I hope we can talk again some day.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


MENU_HANDLER = MessageHandler(
    Filters.regex(
        "^(Begin|💵 Current value|🚨 Panic button|📈 Progress|➗ Current ratios|🔀 Next coin|🔍 Check bot status|⌛ Trade History|🛠 Maintenance|"
        "⚙️ Configurations|▶ Start trade bot|⏹ Stop trade bot|📜 Read last log lines|❌ Delete database|"
        "⚙ Edit user.cfg|👛 Edit coin list|📤 Export database|⬆ Update Telegram Bot|⬆ Update Binance Trade Bot|"
        "🤖 Execute custom script|⬅️ Back|Go back|OK|Cancel update|Cancel|OK 👌|Great 👌)$"
    ),
    menu,
)

ENTRY_POINT_HANDLER = CommandHandler(
    "start", start, Filters.chat(chat_id=eval(settings.CHAT_ID))
)

EDIT_COIN_LIST_HANDLER = MessageHandler(Filters.regex("(.*?)"), edit_coin)

EDIT_USER_CONFIG_HANDLER = MessageHandler(Filters.regex("(.*?)"), edit_user_config)

DELETE_DB_HANDLER = MessageHandler(Filters.regex("^(⚠ Confirm|Go back)$"), delete_db)

UPDATE_TG_HANDLER = MessageHandler(
    Filters.regex("^(Update|Cancel update)$"), update_tg_bot
)

UPDATE_BTB_HANDLER = MessageHandler(
    Filters.regex("^(Update|Cancel update)$"), update_btb
)

PANIC_BUTTON_HANDLER = MessageHandler(
    Filters.regex(
        "^(⚠ Stop & sell at market price|⚠ Stop & cancel order|⚠ Stop the bot|Go back)$"
    ),
    panic,
)

CUSTOM_SCRIPT_HANDLER = MessageHandler(Filters.regex("(.*?)"), execute_custom_script)

FALLBACK_HANDLER = CommandHandler("cancel", cancel)
