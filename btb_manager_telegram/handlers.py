import os
import subprocess
from shutil import copyfile

from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from btb_manager_telegram import (
    DELETE_DB,
    EDIT_COIN_LIST,
    EDIT_USER_CONFIG,
    MENU,
    UPDATE_BTB,
    UPDATE_TG,
    buttons,
    logger,
    settings,
)
from btb_manager_telegram.utils import (
    find_and_kill_binance_trade_bot_process,
    kill_btb_manager_telegram_process,
)


def menu(update: Update, _: CallbackContext) -> int:
    logger.info(f"Menu selector. ({update.message.text})")

    keyboard = [
        [
            "💵 Current value",
        ],
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
        for mes in buttons.current_value():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
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
        re = buttons.delete_db()
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
        re = buttons.edit_user_cfg()
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
        re = buttons.edit_coin()
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
        re = buttons.export_db()
        update.message.reply_text(
            re[0], reply_markup=reply_markup_config, parse_mode="MarkdownV2"
        )
        if re[1] is not None:
            bot = Bot(settings.TOKEN)
            bot.send_document(
                chat_id=update.message.chat_id,
                document=re[1],
                filename="crypto_trading.db",
            )

    elif update.message.text == "Update Telegram Bot":
        re = buttons.update_tg_bot()
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
        re = buttons.update_btb()
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


def start(update: Update, _: CallbackContext) -> int:
    logger.info("Started conversation.")

    keyboard = [["Begin"]]
    message = (
        f"Hi *{update.message.from_user.first_name}*\!\n"
        f"Welcome to _Binace Trade Bot Manager Telegram_\.\n\n"
        f"This Telegram bot was developed by @lorcalhost\.\n"
        f"Find out more about the project [here](https://github.com/lorcalhost/BTB-manager-telegram)\.\n\n"
        f"If you like the bot please [consider supporting the project 🍻](https://www.buymeacoffee.com/lorcalhost)\."
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
            copyfile(coin_file_path, f"{coin_file_path}.backup")
            with open(coin_file_path, "w") as f:
                f.write(update.message.text + "\n")
        except Exception as e:
            logger.error(f"❌ Unable to edit coin list file: {e}")
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
            copyfile(user_cfg_file_path, f"{user_cfg_file_path}.backup")
            with open(user_cfg_file_path, "w") as f:
                f.write(update.message.text + "\n\n\n")
        except Exception as e:
            logger.error(f"❌ Unable to edit user configuration file: {e}")
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
            copyfile(db_file_path, f"{db_file_path}.backup")
            os.remove(db_file_path)
        except Exception as e:
            logger.error(f"❌ Unable to delete database file: {e}")
            message = "❌ Unable to delete database file\."
        try:
            with open(log_file_path, "w") as f:
                f.truncate()
        except Exception as e:
            logger.error(f"❌ Unable to clear log file: {e}")
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
            subprocess.call(
                f"git pull && $(which python3) -m pip install -r requirements.txt --upgrade && "
                f'$(which python3) -m btb_manager_telegram -p "{settings.ROOT_PATH}" &',
                shell=True,
            )
            kill_btb_manager_telegram_process()
        except Exception as e:
            logger.error(f"❌ Unable to update BTB Manager Telegram: {e}")
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
                f"$(which python3) -m pip install -r requirements.txt --upgrade",
                shell=True,
            )
        except Exception as e:
            logger.error(f"Unable to update Binance Trade Bot: {e}")
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


def cancel(update: Update, _: CallbackContext) -> int:
    logger.info("Conversation canceled.")

    update.message.reply_text(
        "Bye! I hope we can talk again some day.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


MENU_HANDLER = MessageHandler(
    Filters.regex(
        "^(Begin|💵 Current value|📈 Progress|➗ Current ratios|🔍 Check bot status|⌛ Trade History|🛠 Maintenance|"
        "⚙️ Configurations|▶ Start trade bot|⏹ Stop trade bot|📜 Read last log lines|❌ Delete database|"
        "⚙ Edit user.cfg|👛 Edit coin list|📤 Export database|Update Telegram Bot|Update Binance Trade Bot|"
        "⬅️ Back|Go back|OK|Cancel update|OK 👌)$"
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

FALLBACK_HANDLER = CommandHandler("cancel", cancel)
