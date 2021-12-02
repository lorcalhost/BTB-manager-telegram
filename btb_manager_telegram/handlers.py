import json
import os
import shutil
import sqlite3
import subprocess
import sys
import traceback
from configparser import ConfigParser

import numpy as np
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
    CREATE_GRAPH,
    CUSTOM_SCRIPT,
    DELETE_DB,
    EDIT_COIN_LIST,
    EDIT_USER_CONFIG,
    GRAPH_MENU,
    MENU,
    PANIC_BUTTON,
    SELLING,
    SOLD,
    UPDATE_BTB,
    UPDATE_TG,
    buttons,
    keyboards,
    logger,
    settings,
)
from btb_manager_telegram.binance_api_utils import send_signed_request
from btb_manager_telegram.report import get_graph
from btb_manager_telegram.utils import (
    escape_tg,
    find_and_kill_binance_trade_bot_process,
    get_custom_scripts_keyboard,
    i18n_format,
    kill_btb_manager_telegram_process,
    reply_text_escape,
    telegram_text_truncator,
)


def menu(update: Update, _: CallbackContext) -> int:
    logger.info(f"Menu selector. ({update.message.text})")

    # Panic button disabled until PR #74 is complete
    # keyboard = [
    #     [i18n_format('keyboard.current_value'), i18n_format('keyboard.current_ratios')],
    #     [i18n_format('keyboard.progress'), i18n_format('keyboard.trade_history')],
    #     [i18n_format('keyboard.check_status'), i18n_format('keyboard.panic')],
    #     [i18n_format('keyboard.maintenance'), i18n_format('keyboard.configurations')],
    # ]

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text == "/start":
        logger.info("Started conversation.")
        message = (
            f"{i18n_format('conversation_started')}\n" f"{i18n_format('select_option')}"
        )
        settings.CHAT.send_message(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )

    if update.message.text in [
        i18n_format("keyboard.back"),
        i18n_format("keyboard.great"),
    ]:
        reply_text_escape_fun(
            i18n_format("select_option"),
            reply_markup=keyboards.menu,
            parse_mode="MarkdownV2",
        )

    elif update.message.text in [
        i18n_format("keyboard.go_back"),
        i18n_format("keyboard.ok"),
        i18n_format("keyboard.configurations"),
    ]:
        reply_text_escape_fun(
            i18n_format("select_option"),
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text in [
        i18n_format("keyboard.maintenance"),
        i18n_format("keyboard.cancel_update"),
        i18n_format("keyboard.cancel"),
        i18n_format("keyboard.ok_s"),
    ]:
        reply_text_escape_fun(
            i18n_format("select_option"),
            reply_markup=keyboards.maintenance,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n_format("keyboard.current_value"):
        for mes in buttons.current_value():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n_format("keyboard.panic"):
        message, status = buttons.panic_btn()
        if status in [BOUGHT, BUYING, SOLD, SELLING]:
            if status == BOUGHT:
                kb = [
                    [i18n_format("keyboard.stop_sell")],
                    [i18n_format("keyboard.go_back")],
                ]
            elif status in [BUYING, SELLING]:
                kb = [
                    [i18n_format("keyboard.stop_cancel")],
                    [i18n_format("keyboard.go_back")],
                ]
            elif status == SOLD:
                kb = [[i18n_format("keyboard.stop")], [i18n_format("keyboard.go_back")]]

            reply_text_escape_fun(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return PANIC_BUTTON

        else:
            reply_text_escape_fun(
                message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n_format("keyboard.progress"):
        for mes in buttons.check_progress():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n_format("keyboard.current_ratios"):
        for mes in buttons.current_ratios():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n_format("keyboard.next_coin"):
        for mes in buttons.next_coin():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n_format("keyboard.check_status"):
        reply_text_escape_fun(
            buttons.check_status(), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )

    elif update.message.text == i18n_format("keyboard.trade_history"):
        for mes in buttons.trade_history():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n_format("keyboard.graph"):
        if os.path.isfile("data/favourite_graphs.npy"):
            favourite_graphs = np.load(
                "data/favourite_graphs.npy", allow_pickle=True
            ).tolist()
            favourite_graphs.sort(key=lambda x: x[1])
            kb = [[i[0]] for i in favourite_graphs[:4]]
            kb.append(
                [i18n_format("keyboard.new_graph"), i18n_format("keyboard.go_back")]
            )
            message = i18n_format("graph.msg_existing_graphs")
        else:
            message = i18n_format("graph.msg_no_graphs")
            kb = [[i18n_format("keyboard.new_graph"), i18n_format("keyboard.go_back")]]
        reply_markup_graph = ReplyKeyboardMarkup(kb, resize_keyboard=True)
        reply_text_escape_fun(
            message, reply_markup=reply_markup_graph, parse_mode="MarkdownV2"
        )
        return GRAPH_MENU

    elif update.message.text == i18n_format("keyboard.start"):
        logger.info("Start bot button pressed.")

        reply_text_escape_fun(
            i18n_format("btb.starting"),
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )
        status = buttons.start_bot()
        message = [
            i18n_format("btb.already_running"),
            i18n_format("btb.started"),
            i18n_format("btb.start_error"),
            f"{i18n_format('btb.installation_path_error', path=settings.ROOT_PATH)}\n{i18n_format('btb.directory_hint')}",
            f"{i18n_format('btb.lib_error', path=settings.PYTHON_PATH)}\n",
        ][status]
        reply_text_escape_fun(
            message,
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n_format("keyboard.stop"):
        reply_text_escape_fun(
            buttons.stop_bot(),
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n_format("keyboard.read_logs"):
        reply_text_escape_fun(
            buttons.read_log(),
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n_format("keyboard.delete_db"):
        message, status = buttons.delete_db()
        if status:
            kb = [[i18n_format("keyboard.confirm"), i18n_format("keyboard.go_back")]]
            reply_text_escape_fun(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return DELETE_DB
        else:
            reply_text_escape_fun(
                message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n_format("keyboard.edit_cfg"):
        message, status = buttons.edit_user_cfg()
        if status:
            reply_text_escape_fun(
                message, reply_markup=ReplyKeyboardRemove(), parse_mode="MarkdownV2"
            )
            return EDIT_USER_CONFIG
        else:
            reply_text_escape_fun(
                message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n_format("keyboard.edit_coin_list"):
        message, status = buttons.edit_coin()
        if status:
            reply_text_escape_fun(
                message, reply_markup=ReplyKeyboardRemove(), parse_mode="MarkdownV2"
            )
            return EDIT_COIN_LIST
        else:
            reply_text_escape_fun(
                message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n_format("keyboard.export_db"):
        message, document = buttons.export_db()
        reply_text_escape_fun(
            message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
        )
        if document is not None:
            settings.CHAT.send_document(
                document=document,
                filename="crypto_trading.db",
            )

    elif update.message.text == i18n_format("keyboard.update_tgb"):
        message, status = buttons.update_tg_bot()
        if status:
            kb = [
                [i18n_format("keyboard.update"), i18n_format("keyboard.cancel_update")]
            ]
            reply_text_escape_fun(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return UPDATE_TG
        else:
            reply_text_escape_fun(
                message,
                reply_markup=keyboards.maintenance,
                parse_mode="MarkdownV2",
            )

    elif update.message.text == i18n_format("keyboard.update_btb"):
        message, status = buttons.update_btb()
        if status:
            kb = [
                [i18n_format("keyboard.update"), i18n_format("keyboard.cancel_update")]
            ]
            reply_text_escape_fun(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return UPDATE_BTB
        else:
            reply_text_escape_fun(
                message,
                reply_markup=keyboards.maintenance,
                parse_mode="MarkdownV2",
            )

    elif update.message.text == i18n_format("keyboard.execute_script"):
        kb, status, message = get_custom_scripts_keyboard()
        if status:
            reply_text_escape_fun(
                message,
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return CUSTOM_SCRIPT
        else:
            reply_text_escape_fun(
                message,
                reply_markup=keyboards.maintenance,
                parse_mode="MarkdownV2",
            )

    return MENU


def edit_coin(update: Update, _: CallbackContext) -> int:
    logger.info(f"Editing coin list. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text != "/stop":
        message = (
            f"{i18n_format('coin_list.success')}\n\n"
            f"```\n"
            f"{update.message.text}\n"
            f"```"
        )
        coin_file_path = os.path.join(settings.ROOT_PATH, "supported_coin_list")
        try:
            shutil.copyfile(coin_file_path, f"{coin_file_path}.backup")
            with open(coin_file_path, "w") as f:
                f.write(update.message.text + "\n")
        except Exception as e:
            logger.error(f"❌ Unable to edit coin list file: {e}", exc_info=True)
            message = i18n_format("coin_list.error")
    else:
        message = (
            f"{i18n_format('exited_no_change')}\n"
            f"{i18n_format('coin_list.not_modified')}"
        )

    keyboard = [[i18n_format("keyboard.go_back")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    reply_text_escape_fun(message, reply_markup=reply_markup, parse_mode="MarkdownV2")

    return MENU


def edit_user_config(update: Update, _: CallbackContext) -> int:
    logger.info(f"Editing user configuration. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text != "/stop":
        message = (
            f"{i18n_format('config.success')}\n\n"
            f"```\n"
            f"{update.message.text}\n"
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
            message = i18n_format("config.error")
        try:
            shutil.copymode(user_cfg_file_path, f"{user_cfg_file_path}.backup")
        except:
            pass
    else:
        message = (
            f"{i18n_format('exited_no_change')}\n"
            f"{i18n_format('config.not_modified')}"
        )

    keyboard = [[i18n_format("keyboard.go_back")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    reply_text_escape_fun(message, reply_markup=reply_markup, parse_mode="MarkdownV2")

    return MENU


def delete_db(update: Update, _: CallbackContext) -> int:
    logger.info(
        f"Asking if the user really wants to delete the db. ({update.message.text})"
    )

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text != i18n_format("keyboard.go_back"):
        message = i18n_format("db.delete.success")
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
            message = i18n_format("db.delete.error")
        try:
            with open(log_file_path, "w") as f:
                f.truncate()
        except Exception as e:
            logger.error(f"❌ Unable to clear log file: {e}", exc_info=True)
            message = i18n_format("db.delete.clear_log_error")

    else:
        message = (
            f"{i18n_format('exited_no_change')}\n"
            f"{i18n_format('db.delete.not_deleted')}"
        )

    keyboard = [[i18n_format("keyboard.ok")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    reply_text_escape_fun(message, reply_markup=reply_markup, parse_mode="MarkdownV2")

    return MENU


def update_tg_bot(update: Update, _: CallbackContext) -> int:
    logger.info(f"Updating BTB Manager Telegram. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text != i18n_format("keyboard.cancel_update"):
        message = i18n_format("update.tgb.updating")
        keyboard = [["/start"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        reply_text_escape_fun(
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
            message = i18n_format("update.tgb.error")
            reply_text_escape_fun(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
    else:
        message = (
            f"{i18n_format('exited_no_change')}\n"
            f"{i18n_format('update.tgb.not_updated')}"
        )
        keyboard = [[i18n_format("keyboard.ok_s")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        reply_text_escape_fun(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    return MENU


def update_btb(update: Update, _: CallbackContext) -> int:
    logger.info(f"Updating Binance Trade Bot. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    keyboard = [[i18n_format("keyboard.ok_s")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    if update.message.text != i18n_format("keyboard.cancel_update"):
        message = (
            f"{i18n_format('update.btb.updating')}\n"
            f"{i18n_format('update.btb.start_manually')}"
        )
        reply_text_escape_fun(
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
            reply_text_escape_fun(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
    else:
        message = (
            f"{i18n_format('exited_no_change')}\n"
            f"{i18n_format('update.btb.not_updated')}"
        )
        reply_text_escape_fun(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    return MENU


def panic(update: Update, _: CallbackContext) -> int:
    logger.info(f"Panic Button is doing its job. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    keyboard = [[i18n_format("keyboard.great")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    if update.message.text != i18n_format("keyboard.go_back"):
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

        if update.message.text != i18n_format("keyboard.stop_sell"):
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

        if update.message.text != i18n_format("keyboard.stop_cancel"):
            params = {"symbol": f"{alt_coin_id}{crypto_coin_id}"}
            message = send_signed_request(
                api_key,
                api_secret_key,
                f"https://api.binance.{tld}",
                "DELETE",
                "/api/v3/openOrders",
                payload=params,
            )

        if update.message.text != i18n_format("keyboard.stop_bot"):
            message = i18n_format("killed_bot")
    else:
        message = (
            f"{i18n_format('exited_no_change')}\n"
            f"{i18n_format('update.btb.not_updated')}"
        )

    reply_text_escape_fun(message, reply_markup=reply_markup, parse_mode="MarkdownV2")
    return MENU


def execute_custom_script(update: Update, _: CallbackContext) -> int:
    logger.info(f"Going to 🤖 execute custom script. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    keyboard = [[i18n_format("keyboard.ok_s")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    custom_scripts_path = "./config/custom_scripts.json"
    if update.message.text != i18n_format("keyboard.cancel"):
        with open(custom_scripts_path) as f:
            scripts = json.load(f)

            try:
                command = ["bash", "-c", str(scripts[update.message.text])]
            except Exception as e:
                logger.error(
                    f"Unable to find script named {update.message.text} in custom_scripts.json file: {e}",
                    exc_info=True,
                )
                message = i18n_format("script.not_found", name=update.message.text)
                reply_text_escape_fun(
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
                    reply_text_escape_fun(
                        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                    )
            except Exception as e:
                logger.error(f"Error during script execution: {e}", exc_info=True)
                message = i18n_format("script.error")
                reply_text_escape_fun(
                    message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )

    return MENU


def graph_menu(update: Update, _: CallbackContext) -> int:
    if update.message.text == i18n_format("keyboard.go_back"):
        message = i18n_format("graph.exit")
        update.message.reply_text(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )
        return MENU
    if update.message.text == i18n_format("keyboard.new_graph"):
        message = f"""{i18n_format("graph.new_graph.a")}
{i18n_format("graph.new_graph.b")}
{i18n_format("graph.new_graph.c")}
{i18n_format("graph.new_graph.d")}
{i18n_format("graph.new_graph.e")}
- {i18n_format("graph.new_graph.f")}
- {i18n_format("graph.new_graph.g")}
- {i18n_format("graph.new_graph.h")}
{i18n_format("graph.new_graph.i")}"""
        update.message.reply_text(
            escape_tg(message),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="MarkdownV2",
        )
        return CREATE_GRAPH
    else:
        return create_graph(update=update, _=_)


def create_graph(update: Update, _: CallbackContext) -> int:
    text = update.message.text

    if text == "/stop":
        message = i18n_format("graph.exit")
        update.message.reply_text(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )
        return MENU

    text = [i for i in text.split(" ") if i != ""]

    if not (len(text) == 2 and text[1].isdigit()):
        message = i18n_format("graph.bad_graph")
        update.message.reply_text(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )
        return MENU

    days = int(text[1])
    coins = text[0].upper().split(",")
    coins.sort()
    input_text_filtered = f"{','.join(coins)} {days}"

    try:
        figname, nb_plot = get_graph(False, coins, days, "amount", "USD")
    except Exception as e:
        message = f"{i18n_format('graph.error')}\n ```\n"
        message += "".join(traceback.format_exception(*sys.exc_info()))
        message += "\n```"
        update.message.reply_text(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )
        return MENU

    if nb_plot <= 1:
        message = i18n_format("graph.not_enough_points")
        update.message.reply_text(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )
        return MENU

    if os.path.isfile("data/favourite_graphs.npy"):
        favourite_graphs = np.load(
            "data/favourite_graphs.npy", allow_pickle=True
        ).tolist()
    else:
        favourite_graphs = []
    found = False
    for index, (graph, nb_calls) in enumerate(favourite_graphs):
        if graph == input_text_filtered:
            favourite_graphs[index][1] = int(nb_calls) + 1
            found = True
            break
    if not found:
        favourite_graphs.append([input_text_filtered, 1])
    np.save("data/favourite_graphs.npy", favourite_graphs, allow_pickle=True)

    with open(figname, "rb") as f:
        update.message.reply_photo(
            f, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )

    return MENU


def cancel(update: Update, _: CallbackContext) -> int:
    logger.info("Conversation canceled.")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    reply_text_escape_fun(
        i18n_format("bye"), reply_markup=ReplyKeyboardRemove(), parse_mode="MarkdownV2"
    )
    return ConversationHandler.END


MENU_HANDLER = MessageHandler(
    Filters.regex(
        f"^({i18n_format('keyboard.current_value')}|{i18n_format('keyboard.panic')}|{i18n_format('keyboard.progress')}|{i18n_format('keyboard.current_ratios')}|{i18n_format('keyboard.next_coin')}|{i18n_format('keyboard.check_status')}|{i18n_format('keyboard.trade_history')}|{i18n_format('keyboard.graph')}|{i18n_format('keyboard.maintenance')}|"
        f"{i18n_format('keyboard.configurations')}|{i18n_format('keyboard.start')}|{i18n_format('keyboard.stop')}|{i18n_format('keyboard.read_logs')}|{i18n_format('keyboard.delete_db')}|"
        f"{i18n_format('keyboard.edit_cfg')}|{i18n_format('keyboard.edit_coin_list')}|{i18n_format('keyboard.export_db')}|{i18n_format('keyboard.update_tgb')}|{i18n_format('keyboard.update_btb')}|"
        f"{i18n_format('keyboard.execute_script')}|{i18n_format('keyboard.back')}|{i18n_format('keyboard.go_back')}|{i18n_format('keyboard.ok')}|{i18n_format('keyboard.cancel_update')}|{i18n_format('keyboard.cancel')}|{i18n_format('keyboard.ok_s')}|{i18n_format('keyboard.great')})$"
    ),
    menu,
)

ENTRY_POINT_HANDLER = CommandHandler(
    "start", menu, Filters.chat(chat_id=eval(settings.CHAT_ID))
)

EDIT_COIN_LIST_HANDLER = MessageHandler(Filters.regex("(.*?)"), edit_coin)

EDIT_USER_CONFIG_HANDLER = MessageHandler(Filters.regex("(.*?)"), edit_user_config)

DELETE_DB_HANDLER = MessageHandler(
    Filters.regex(
        f"^({i18n_format('keyboard.confirm')}|{i18n_format('keyboard.go_back')})$"
    ),
    delete_db,
)

UPDATE_TG_HANDLER = MessageHandler(
    Filters.regex(
        f"^({i18n_format('keyboard.update')}|{i18n_format('keyboard.cancel_update')})$"
    ),
    update_tg_bot,
)

UPDATE_BTB_HANDLER = MessageHandler(
    Filters.regex(
        f"^({i18n_format('keyboard.update')}|{i18n_format('keyboard.cancel_update')})$"
    ),
    update_btb,
)

PANIC_BUTTON_HANDLER = MessageHandler(
    Filters.regex(
        f"^({i18n_format('keyboard.stop_sell')}|{i18n_format('keyboard.stop_cancel')}|{i18n_format('keyboard.stop_bot')}|{i18n_format('keyboard.go_back')})$"
    ),
    panic,
)

CUSTOM_SCRIPT_HANDLER = MessageHandler(Filters.regex("(.*?)"), execute_custom_script)

GRAPH_MENU_HANDLER = MessageHandler(Filters.regex("(.*)"), graph_menu)

CREATE_GRAPH_HANDLER = MessageHandler(Filters.regex("(.*)"), create_graph)


FALLBACK_HANDLER = CommandHandler("cancel", cancel)
