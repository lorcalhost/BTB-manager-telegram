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

import i18n
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
    escape_tg
)


def menu(update: Update, _: CallbackContext) -> int:
    logger.info(f"Menu selector. ({update.message.text})")

    # Panic button disabled until PR #74 is complete
    # keyboard = [
    #     [i18n.t('keyboard.current_value'), i18n.t('keyboard.current_ratios')],
    #     [i18n.t('keyboard.progress'), i18n.t('keyboard.trade_history')],
    #     [i18n.t('keyboard.check_status'), i18n.t('keyboard.panic')],
    #     [i18n.t('keyboard.maintenance'), i18n.t('keyboard.configurations')],
    # ]

    keyboard = [
        [i18n.t("keyboard.current_value"), i18n.t("keyboard.progress")],
        [i18n.t("keyboard.current_ratios"), i18n.t("keyboard.next_coin")],
        [i18n.t("keyboard.check_status"), i18n.t("keyboard.trade_history")],
        [i18n.t("keyboard.maintenance"), i18n.t("keyboard.configurations")],
    ]

    config_keyboard = [
        [i18n.t("keyboard.start"), i18n.t("keyboard.stop")],
        [i18n.t("keyboard.read_logs"), i18n.t("keyboard.delete_db")],
        [i18n.t("keyboard.edit_cfg"), i18n.t("keyboard.edit_coin_list")],
        [i18n.t("keyboard.export_db"), i18n.t("keyboard.back")],
    ]

    maintenance_keyboard = [
        [i18n.t("keyboard.update_tgb")],
        [i18n.t("keyboard.update_btb")],
        [i18n.t("keyboard.execute_script")],
        [i18n.t("keyboard.back")],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    reply_markup_config = ReplyKeyboardMarkup(config_keyboard, resize_keyboard=True)

    reply_markup_maintenance = ReplyKeyboardMarkup(
        maintenance_keyboard, resize_keyboard=True
    )

    if update.message.text in [
        i18n.t("keyboard.begin"),
        i18n.t("keyboard.back"),
        i18n.t("keyboard.great"),
    ]:
        message = i18n.t("select_option")
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    elif update.message.text in [
        i18n.t("keyboard.go_back"),
        i18n.t("keyboard.ok"),
        i18n.t("keyboard.configurations"),
    ]:
        message = i18n.t("select_option")
        update.message.reply_text(
            message, reply_markup=reply_markup_config, parse_mode="MarkdownV2"
        )

    elif update.message.text in [
        i18n.t("keyboard.maintenance"),
        i18n.t("keyboard.cancel_update"),
        i18n.t("keyboard.cancel"),
        i18n.t("keyboard.ok_s"),
    ]:
        message = i18n.t("select_option")
        update.message.reply_text(
            message, reply_markup=reply_markup_maintenance, parse_mode="MarkdownV2"
        )

    elif update.message.text == i18n.t("keyboard.current_value"):
        for mes in buttons.current_value():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.panic"):
        message, status = buttons.panic_btn()
        if status in [BOUGHT, BUYING, SOLD, SELLING]:
            if status == BOUGHT:
                kb = [[i18n.t("keyboard.stop_sell")], [i18n.t("keyboard.go_back")]]
            elif status in [BUYING, SELLING]:
                kb = [[i18n.t("keyboard.stop_cancel")], [i18n.t("keyboard.go_back")]]
            elif status == SOLD:
                kb = [[i18n.t("keyboard.stop")], [i18n.t("keyboard.go_back")]]

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

    elif update.message.text == i18n.t("keyboard.progress"):
        for mes in buttons.check_progress():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.current_ratios"):
        for mes in buttons.current_ratios():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.next_coin"):
        for mes in buttons.next_coin():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.check_status"):
        update.message.reply_text(
            buttons.check_status(), reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    elif update.message.text == i18n.t("keyboard.trade_history"):
        for mes in buttons.trade_history():
            update.message.reply_text(
                mes, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.start"):
        update.message.reply_text(
            buttons.start_bot(),
            reply_markup=reply_markup_config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n.t("keyboard.stop"):
        update.message.reply_text(
            buttons.stop_bot(),
            reply_markup=reply_markup_config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n.t("keyboard.read_logs"):
        update.message.reply_text(
            buttons.read_log(),
            reply_markup=reply_markup_config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n.t("keyboard.delete_db"):
        message, status = buttons.delete_db()
        if status:
            kb = [[i18n.t("keyboard.confirm"), i18n.t("keyboard.go_back")]]
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

    elif update.message.text == i18n.t("keyboard.edit_cfg"):
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

    elif update.message.text == i18n.t("keyboard.edit_coin_list"):
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

    elif update.message.text == i18n.t("keyboard.export_db"):
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

    elif update.message.text == i18n.t("keyboard.update_tgb"):
        message, status = buttons.update_tg_bot()
        if status:
            kb = [[i18n.t("keyboard.update"), i18n.t("keyboard.cancel_update")]]
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

    elif update.message.text == i18n.t("keyboard.update_btb"):
        message, status = buttons.update_btb()
        if status:
            kb = [[i18n.t("keyboard.update"), i18n.t("keyboard.cancel_update")]]
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

    elif update.message.text == i18n.t("keyboard.execute_script"):
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

    keyboard = [[i18n.t("keyboard.begin")]]
    message = (
        f"Hi *{escape_markdown(update.message.from_user.first_name, version=2)}*\!\n"
        f"{i18n.t('welcome')}\n\n"
        f"{i18n.t('developed_by')}\n"
        f"{i18n.t('project_link')}\n\n"
        f"{i18n.t('donation')}"
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

    if update.message.text != i18n.t("stop_cmd"):
        message = (
            f"{i18n.t('keyboard.edited_coin_list')}\n\n"
            f"```\n"
            f"{escape_tg(update.message.text)}\n"
            f"```"
        )
        coin_file_path = os.path.join(settings.ROOT_PATH, "supported_coin_list")
        try:
            shutil.copyfile(coin_file_path, f"{coin_file_path}.backup")
            with open(coin_file_path, "w") as f:
                f.write(update.message.text + "\n")
        except Exception as e:
            logger.error(f"❌ Unable to edit coin list file: {e}", exc_info=True)
            message = i18n.t("coin_edit_error")
    else:
        message = (
            f"{i18n.t('exited_no_change')}\n" f"{i18n.t('coin_list_not_modified')}"
        )

    keyboard = [[i18n.t("keyboard.go_back")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
    )

    return MENU


def edit_user_config(update: Update, _: CallbackContext) -> int:
    logger.info(f"Editing user configuration. ({update.message.text})")

    if update.message.text != i18n.t("stop_cmd"):
        message = (
            f"{i18n.t('edited_user_config')}\n\n"
            f"```\n"
            f"{escape_tg(update.message.text)}\n"
            f"```"
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
            message = i18n.t("user_config_error")
    else:
        message = (
            f"{i18n.t('exited_no_change')}\n" f"{i18n.t('user_config_not_modified')}"
        )

    keyboard = [[i18n.t("keyboard.go_back")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
    )

    return MENU


def delete_db(update: Update, _: CallbackContext) -> int:
    logger.info(
        f"Asking if the user really wants to delete the db. ({update.message.text})"
    )

    if update.message.text != i18n.t("keyboard.go_back"):
        message = i18n.t("deleted_db")
        db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
        pw_file_path = os.path.join(settings.ROOT_PATH, "data/paper_wallet.json")
        log_file_path = os.path.join(settings.ROOT_PATH, "logs/crypto_trading.log")
        try:
            shutil.copyfile(db_file_path, f"{db_file_path}.backup")
            os.remove(db_file_path)
            if os.path.isfile(pw_file_path):
                shutil.copyfile(pw_file_path, f"{pw_file_path}.backup")
                os.remove(pw_file_path)
        except Exception as e:
            logger.error(f"❌ Unable to delete database file: {e}", exc_info=True)
            message = i18n.t("delete_db_error")
        try:
            with open(log_file_path, "w") as f:
                f.truncate()
        except Exception as e:
            logger.error(f"❌ Unable to clear log file: {e}", exc_info=True)
            message = i18n.t("clear_log_error")

    else:
        message = f"{i18n.t('exited_no_change')}\n" f"{i18n.t('db_not_deleted')}"

    keyboard = [[i18n.t("keyboard.ok")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
    )

    return MENU


def update_tg_bot(update: Update, _: CallbackContext) -> int:
    logger.info(f"Updating BTB Manager Telegram. ({update.message.text})")

    if update.message.text != i18n.t("keyboard.cancel_update"):
        message = f"{i18n.t('tgb_updating')}\n" f"{i18n.t('wait_then_start')}"
        keyboard = [[i18n.t("start_cmd")]]
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
            message = i18n.t("tgb_update_error")
            update.message.reply_text(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
    else:
        message = f"{i18n.t('exited_no_change')}\n" f"{i18n.t('tgb_not_updated')}"
        keyboard = [[i18n.t("keyboard.ok_s")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    return MENU


def update_btb(update: Update, _: CallbackContext) -> int:
    logger.info(f"Updating Binance Trade Bot. ({update.message.text})")

    keyboard = [[i18n.t("keyboard.ok_s")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    if update.message.text != i18n.t("keyboard.cancel_update"):
        message = f"{i18n.t('btb_updating')}\n" f"{i18n.t('wait_then_start_manually')}"
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
        message = f"{i18n.t('exited_no_change')}\n" f"{i18n.t('btb_bot_updated')}"
        update.message.reply_text(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    return MENU


def panic(update: Update, _: CallbackContext) -> int:
    logger.info(f"Panic Button is doing its job. ({update.message.text})")

    keyboard = [[i18n.t("keyboard.great")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    if update.message.text != i18n.t("keyboard.go_back"):
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

        if update.message.text != i18n.t("keyboard.stop_sell"):
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

        if update.message.text != i18n.t("keyboard.stop_cancel"):
            params = {"symbol": f"{alt_coin_id}{crypto_coin_id}"}
            message = send_signed_request(
                api_key,
                api_secret_key,
                f"https://api.binance.{tld}",
                "DELETE",
                "/api/v3/openOrders",
                payload=params,
            )

        if update.message.text != i18n.t("keyboard.stop_bot"):
            message = i18n.t("killed_bot")
    else:
        message = f"{i18n.t('exited_no_change')}\n" f"{i18n.t('btb_not_updated')}"

    update.message.reply_text(
        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
    )
    return MENU


def execute_custom_script(update: Update, _: CallbackContext) -> int:
    logger.info(f"Going to 🤖 execute custom script. ({update.message.text})")

    keyboard = [[i18n.t("keyboard.ok_s")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    custom_scripts_path = "./config/custom_scripts.json"
    if update.message.text != i18n.t("keyboard.cancel"):
        with open(custom_scripts_path) as f:
            scripts = json.load(f)

            try:
                command = ["bash", "-c", str(scripts[update.message.text])]
            except Exception as e:
                logger.error(
                    f"Unable to find script named {update.message.text} in custom_scripts.json file: {e}",
                    exc_info=True,
                )
                message = f"{i18n.t('script_not_found', name=escape_markdown(update.message.text, version=2))}"
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
                message = i18n.t("script_error")
                update.message.reply_text(
                    message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )

    return MENU


def cancel(update: Update, _: CallbackContext) -> int:
    logger.info("Conversation canceled.")

    update.message.reply_text(
        i18n.t("bye"), reply_markup=ReplyKeyboardRemove(), parse_mode="MarkdownV2"
    )
    return ConversationHandler.END


MENU_HANDLER = MessageHandler(
    Filters.regex(
        f"^({i18n.t('keyboard.begin')}|{i18n.t('keyboard.current_value')}|{i18n.t('keyboard.panic')}|{i18n.t('keyboard.progress')}|{i18n.t('keyboard.current_ratios')}|{i18n.t('keyboard.next_coin')}|{i18n.t('keyboard.check_status')}|{i18n.t('keyboard.trade_history')}|{i18n.t('keyboard.maintenance')}|"
        f"{i18n.t('keyboard.configurations')}|{i18n.t('keyboard.start')}|{i18n.t('keyboard.stop')}|{i18n.t('keyboard.read_logs')}|{i18n.t('keyboard.delete_db')}|"
        f"{i18n.t('keyboard.edit_cfg')}|{i18n.t('keyboard.edit_coin_list')}|{i18n.t('keyboard.export_db')}|{i18n.t('keyboard.update_tgb')}|{i18n.t('keyboard.update_btb')}|"
        f"{i18n.t('keyboard.execute_script')}|{i18n.t('keyboard.back')}|{i18n.t('keyboard.go_back')}|{i18n.t('keyboard.ok')}|{i18n.t('keyboard.cancel_update')}|{i18n.t('keyboard.cancel')}|{i18n.t('keyboard.ok_s')}|{i18n.t('keyboard.great')})$"
    ),
    menu,
)

ENTRY_POINT_HANDLER = CommandHandler(
    "start", start, Filters.chat(chat_id=eval(settings.CHAT_ID))
)

EDIT_COIN_LIST_HANDLER = MessageHandler(Filters.regex("(.*?)"), edit_coin)

EDIT_USER_CONFIG_HANDLER = MessageHandler(Filters.regex("(.*?)"), edit_user_config)

DELETE_DB_HANDLER = MessageHandler(
    Filters.regex(f"^({i18n.t('keyboard.confirm')}|{i18n.t('keyboard.go_back')})$"),
    delete_db,
)

UPDATE_TG_HANDLER = MessageHandler(
    Filters.regex(
        f"^({i18n.t('keyboard.update')}|{i18n.t('keyboard.cancel_confirm')})$"
    ),
    update_tg_bot,
)

UPDATE_BTB_HANDLER = MessageHandler(
    Filters.regex(
        f"^({i18n.t('keyboard.update')}|{i18n.t('keyboard.cancel_confirm')})$"
    ),
    update_btb,
)

PANIC_BUTTON_HANDLER = MessageHandler(
    Filters.regex(
        f"^({i18n.t('keyboard.stop_sell')}|{i18n.t('keyboard.stop_cancel')}|{i18n.t('keyboard.stop_bot')}|{i18n.t('keyboard.go_back')})$"
    ),
    panic,
)

CUSTOM_SCRIPT_HANDLER = MessageHandler(Filters.regex("(.*?)"), execute_custom_script)

FALLBACK_HANDLER = CommandHandler("cancel", cancel)
