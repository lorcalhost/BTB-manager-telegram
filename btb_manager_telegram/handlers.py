import configparser
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback

import i18n
import numpy as np
import telegram
import telegram.ext

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
    settings,
)
from btb_manager_telegram.binance_api_utils import send_signed_request
from btb_manager_telegram.formating import (
    escape_tg,
    reply_text_escape,
    telegram_text_truncator,
)
from btb_manager_telegram.logging import logger
from btb_manager_telegram.report import get_graph
from btb_manager_telegram.utils import (
    find_and_kill_binance_trade_bot_process,
    get_custom_scripts_keyboard,
    get_restart_file_name,
    kill_btb_manager_telegram_process,
)


def menu(update, _):
    logger.info(f"Menu selector. ({update.message.text})")

    # Panic button disabled until PR #74 is complete
    # keyboard = [
    #     [i18n.t('keyboard.current_value'), i18n.t('keyboard.current_ratios')],
    #     [i18n.t('keyboard.progress'), i18n.t('keyboard.trade_history')],
    #     [i18n.t('keyboard.check_status'), i18n.t('keyboard.panic')],
    #     [i18n.t('keyboard.maintenance'), i18n.t('keyboard.configurations')],
    # ]

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text == "/start":
        logger.info("Started conversation.")
        message = f"{i18n.t('conversation_started')}\n" f"{i18n.t('select_option')}"
        settings.CHAT.send_message(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )

    if update.message.text in [
        i18n.t("keyboard.back"),
        i18n.t("keyboard.great"),
    ]:
        reply_text_escape_fun(
            i18n.t("select_option"),
            reply_markup=keyboards.menu,
            parse_mode="MarkdownV2",
        )

    elif update.message.text in [
        i18n.t("keyboard.go_back"),
        i18n.t("keyboard.ok"),
        i18n.t("keyboard.configurations"),
    ]:
        reply_text_escape_fun(
            i18n.t("select_option"),
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text in [
        i18n.t("keyboard.maintenance"),
        i18n.t("keyboard.cancel_update"),
        i18n.t("keyboard.cancel"),
        i18n.t("keyboard.ok_s"),
    ]:
        reply_text_escape_fun(
            i18n.t("select_option"),
            reply_markup=keyboards.maintenance,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n.t("keyboard.current_value"):
        for mes in buttons.current_value():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.panic"):
        message, status = buttons.panic_btn()
        if status in [BOUGHT, BUYING, SOLD, SELLING]:
            if status == BOUGHT:
                kb = [
                    [i18n.t("keyboard.stop_sell")],
                    [i18n.t("keyboard.go_back")],
                ]
            elif status in [BUYING, SELLING]:
                kb = [
                    [i18n.t("keyboard.stop_cancel")],
                    [i18n.t("keyboard.go_back")],
                ]
            elif status == SOLD:
                kb = [[i18n.t("keyboard.stop")], [i18n.t("keyboard.go_back")]]

            reply_text_escape_fun(
                message,
                reply_markup=telegram.ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return PANIC_BUTTON

        else:
            reply_text_escape_fun(
                message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.progress"):
        for mes in buttons.check_progress():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.next_coin"):
        for mes in buttons.next_coin():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.check_status"):
        reply_text_escape_fun(
            buttons.check_status(), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )

    elif update.message.text == i18n.t("keyboard.bot_stats"):
        for mes in buttons.bot_stats():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.trade_history"):
        for mes in buttons.trade_history():
            reply_text_escape_fun(
                mes, reply_markup=keyboards.menu, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.graph"):
        keyboard = []
        if os.path.isfile("data/favourite_graphs.npy"):
            favourite_graphs = np.load(
                "data/favourite_graphs.npy", allow_pickle=True
            ).tolist()
            favourite_graphs.sort(key=lambda x: -int(x[1]))
            favourite_graphs = [i[0] for i in favourite_graphs]
            keyboard.extend(
                [
                    favourite_graphs[3 * i : 3 * i + 3]
                    for i in range(min(3, (len(favourite_graphs) - 1) // 3 + 1))
                ]
            )
            message = i18n.t("graph.msg_existing_graphs")
        else:
            message = i18n.t("graph.msg_no_graphs")
        keyboard.append([i18n.t("keyboard.new_graph"), i18n.t("keyboard.go_back")])
        reply_markup_graph = telegram.ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True
        )
        reply_text_escape_fun(
            message, reply_markup=reply_markup_graph, parse_mode="MarkdownV2"
        )
        return GRAPH_MENU

    elif update.message.text == i18n.t("keyboard.start"):
        logger.info("Start bot button pressed.")

        reply_text_escape_fun(
            i18n.t("btb.starting"),
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )
        status = buttons.start_bot()
        message = [
            i18n.t("btb.already_running"),
            i18n.t("btb.started"),
            i18n.t("btb.start_error"),
            f"{i18n.t('btb.installation_path_error', path=settings.ROOT_PATH)}\n{i18n.t('btb.directory_hint')}",
            f"{i18n.t('btb.lib_error', path=settings.PYTHON_PATH)}\n",
        ][status]
        reply_text_escape_fun(
            message,
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n.t("keyboard.stop"):
        reply_text_escape_fun(
            buttons.stop_bot(),
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n.t("keyboard.read_logs"):
        reply_text_escape_fun(
            buttons.read_log(),
            reply_markup=keyboards.config,
            parse_mode="MarkdownV2",
        )

    elif update.message.text == i18n.t("keyboard.delete_db"):
        message, status = buttons.delete_db()
        if status:
            kb = [[i18n.t("keyboard.confirm"), i18n.t("keyboard.go_back")]]
            reply_text_escape_fun(
                message,
                reply_markup=telegram.ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return DELETE_DB
        else:
            reply_text_escape_fun(
                message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.edit_cfg"):
        message, status = buttons.edit_user_cfg()
        if status:
            reply_text_escape_fun(
                message,
                reply_markup=telegram.ReplyKeyboardRemove(),
                parse_mode="MarkdownV2",
            )
            return EDIT_USER_CONFIG
        else:
            reply_text_escape_fun(
                message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.edit_coin_list"):
        message, status = buttons.edit_coin()
        if status:
            reply_text_escape_fun(
                message,
                reply_markup=telegram.ReplyKeyboardRemove(),
                parse_mode="MarkdownV2",
            )
            return EDIT_COIN_LIST
        else:
            reply_text_escape_fun(
                message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
            )

    elif update.message.text == i18n.t("keyboard.export_db"):
        message, document = buttons.export_db()
        reply_text_escape_fun(
            message, reply_markup=keyboards.config, parse_mode="MarkdownV2"
        )
        if document is not None:
            settings.CHAT.send_document(
                document=document,
                filename="crypto_trading.db",
            )

    elif update.message.text == i18n.t("keyboard.update_tgb"):
        message, status = buttons.update_tg_bot()
        if status:
            kb = [[i18n.t("keyboard.update"), i18n.t("keyboard.cancel_update")]]
            reply_text_escape_fun(
                message,
                reply_markup=telegram.ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return UPDATE_TG
        else:
            reply_text_escape_fun(
                message,
                reply_markup=keyboards.maintenance,
                parse_mode="MarkdownV2",
            )

    elif update.message.text == i18n.t("keyboard.update_btb"):
        message, status = buttons.update_btb()
        if status:
            kb = [[i18n.t("keyboard.update"), i18n.t("keyboard.cancel_update")]]
            reply_text_escape_fun(
                message,
                reply_markup=telegram.ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="MarkdownV2",
            )
            return UPDATE_BTB
        else:
            reply_text_escape_fun(
                message,
                reply_markup=keyboards.maintenance,
                parse_mode="MarkdownV2",
            )

    elif update.message.text == i18n.t("keyboard.execute_script"):
        kb, status, message = get_custom_scripts_keyboard()
        if status:
            reply_text_escape_fun(
                message,
                reply_markup=telegram.ReplyKeyboardMarkup(kb, resize_keyboard=True),
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


def edit_coin(update, _):
    logger.info(f"Editing coin list. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text != "/stop":
        message = (
            f"{i18n.t('coin_list.success')}\n\n"
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
            message = i18n.t("coin_list.error")
    else:
        message = (
            f"{i18n.t('exited_no_change')}\n" f"{i18n.t('coin_list.not_modified')}"
        )

    keyboard = [[i18n.t("keyboard.go_back")]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    reply_text_escape_fun(message, reply_markup=reply_markup, parse_mode="MarkdownV2")

    return MENU


def edit_user_config(update, _):
    logger.info(f"Editing user configuration. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text != "/stop":
        message = (
            f"{i18n.t('config.success')}\n\n" f"```\n" f"{update.message.text}\n" f"```"
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
            message = i18n.t("config.error")
        try:
            shutil.copymode(user_cfg_file_path, f"{user_cfg_file_path}.backup")
        except:
            pass
    else:
        message = f"{i18n.t('exited_no_change')}\n" f"{i18n.t('config.not_modified')}"

    keyboard = [[i18n.t("keyboard.go_back")]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    reply_text_escape_fun(message, reply_markup=reply_markup, parse_mode="MarkdownV2")

    return MENU


def delete_db(update, _):
    logger.info(
        f"Asking if the user really wants to delete the db. ({update.message.text})"
    )

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text != i18n.t("keyboard.go_back"):
        message = i18n.t("db.delete.success")
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
            message = i18n.t("db.delete.error")
        try:
            with open(log_file_path, "w") as f:
                f.truncate()
        except Exception as e:
            logger.error(f"❌ Unable to clear log file: {e}", exc_info=True)
            message = i18n.t("db.delete.clear_log_error")

    else:
        message = f"{i18n.t('exited_no_change')}\n" f"{i18n.t('db.delete.not_deleted')}"

    keyboard = [[i18n.t("keyboard.ok")]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    reply_text_escape_fun(message, reply_markup=reply_markup, parse_mode="MarkdownV2")

    return MENU


def update_tg_bot(update, _):
    logger.info(f"Updating BTB Manager Telegram. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    if update.message.text != i18n.t("keyboard.cancel_update"):
        message = i18n.t("update.tgb.updating")
        keyboard = [["/start"]]
        reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        reply_text_escape_fun(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )
        try:
            manager_python_path = sys.executable
            subprocess.run(
                f"git pull"
                f" && git checkout $(git describe --abbrev=0 --tags)"
                f" && {manager_python_path} -m pip install -r requirements.txt --upgrade"
                f" && {manager_python_path} -m btb_manager_telegram {' '.join(settings.RAW_ARGS)} --_remove_this_arg_auto_restart_old_pid _remove_this_arg_{os.getpid()} &",
                shell=True,
                check=True,
            )
            restart_filename = get_restart_file_name(os.getpid())
            max_attempts = 200
            attempts = 0
            while (not os.path.isfile(restart_filename)) and (attempts < max_attempts):
                # waiting for the tg bot to prove it is alive
                attempts += 1
                time.sleep(0.1)
            if os.path.isfile(restart_filename):
                logger.info(
                    "The old process says : The new process has started. Exiting."
                )
                kill_btb_manager_telegram_process()
            else:
                logger.error(f"Unable to restart the telegram bot")

        except Exception as e:
            logger.error(f"Unable to update BTB Manager Telegram: {e}", exc_info=True)
            message = i18n.t("update.tgb.error")
            reply_text_escape_fun(
                message, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
    else:
        message = (
            f"{i18n.t('exited_no_change')}\n" f"{i18n.t('update.tgb.not_updated')}"
        )
        keyboard = [[i18n.t("keyboard.ok_s")]]
        reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        reply_text_escape_fun(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    return MENU


def update_btb(update, _):
    logger.info(f"Updating Binance Trade Bot. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    keyboard = [[i18n.t("keyboard.ok_s")]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    if update.message.text != i18n.t("keyboard.cancel_update"):
        message = (
            f"{i18n.t('update.btb.updating')}\n"
            f"{i18n.t('update.btb.start_manually')}"
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
            f"{i18n.t('exited_no_change')}\n" f"{i18n.t('update.btb.not_updated')}"
        )
        reply_text_escape_fun(
            message, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )

    return MENU


def panic(update, _):
    logger.info(f"Panic Button is doing its job. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    keyboard = [[i18n.t("keyboard.great")]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
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
            config = configparser.ConfigParser()
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
        message = (
            f"{i18n.t('exited_no_change')}\n" f"{i18n.t('update.btb.not_updated')}"
        )

    reply_text_escape_fun(message, reply_markup=reply_markup, parse_mode="MarkdownV2")
    return MENU


def execute_custom_script(update, _):
    logger.info(f"Going to 🤖 execute custom script. ({update.message.text})")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    keyboard = [[i18n.t("keyboard.ok_s")]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
                message = i18n.t("script.not_found", name=update.message.text)
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
                    output.decode("utf-8"),
                    padding_chars_head="```\n",
                    padding_chars_tail="```",
                )
                for message in message_list:
                    reply_text_escape_fun(
                        message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                    )
            except Exception as e:
                logger.error(f"Error during script execution: {e}", exc_info=True)
                message = i18n.t("script.error")
                reply_text_escape_fun(
                    message, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )

    return MENU


def graph_menu(update, _):
    if update.message.text == i18n.t("keyboard.go_back"):
        message = i18n.t("graph.exit")
        update.message.reply_text(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )
        return MENU
    if update.message.text == i18n.t("keyboard.new_graph"):
        message = f"""{i18n.t("graph.new_graph.a")}
{i18n.t("graph.new_graph.b")}
{i18n.t("graph.new_graph.c")}
{i18n.t("graph.new_graph.d")}
{i18n.t("graph.new_graph.e")}
- {i18n.t("graph.new_graph.f")}
- {i18n.t("graph.new_graph.g")}
- {i18n.t("graph.new_graph.h")}
{i18n.t("graph.new_graph.i")}"""
        update.message.reply_text(
            escape_tg(message),
            reply_markup=telegram.ReplyKeyboardRemove(),
            parse_mode="MarkdownV2",
        )
        return CREATE_GRAPH
    else:
        return create_graph(update=update, _=_)


def create_graph(update, _):
    text = update.message.text

    if text == "/stop":
        message = i18n.t("graph.exit")
        update.message.reply_text(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )
        return MENU

    text = [i for i in text.split(" ") if i != ""]

    if not (len(text) == 2 and text[1].isdigit()):
        message = i18n.t("graph.bad_graph")
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
        message = f"{i18n.t('graph.error')}\n ```\n"
        message += "".join(traceback.format_exception(*sys.exc_info()))
        message += "\n```"
        update.message.reply_text(
            escape_tg(message), reply_markup=keyboards.menu, parse_mode="MarkdownV2"
        )
        return MENU

    if nb_plot <= 1:
        message = i18n.t("graph.not_enough_points")
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


def cancel(update, _):
    logger.info("Conversation canceled.")

    # modify reply_text function to have it escaping characters
    reply_text_escape_fun = reply_text_escape(update.message.reply_text)

    reply_text_escape_fun(
        i18n.t("bye"),
        reply_markup=telegram.ReplyKeyboardRemove(),
        parse_mode="MarkdownV2",
    )
    return telegram.ext.ConversationHandler.END


MENU_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex(
        f"^({i18n.t('keyboard.current_value')}|{i18n.t('keyboard.panic')}|{i18n.t('keyboard.progress')}|{i18n.t('keyboard.next_coin')}|{i18n.t('keyboard.check_status')}|{i18n.t('keyboard.bot_stats')}|{i18n.t('keyboard.trade_history')}|{i18n.t('keyboard.graph')}|{i18n.t('keyboard.maintenance')}|"
        f"{i18n.t('keyboard.configurations')}|{i18n.t('keyboard.start')}|{i18n.t('keyboard.stop')}|{i18n.t('keyboard.read_logs')}|{i18n.t('keyboard.delete_db')}|"
        f"{i18n.t('keyboard.edit_cfg')}|{i18n.t('keyboard.edit_coin_list')}|{i18n.t('keyboard.export_db')}|{i18n.t('keyboard.update_tgb')}|{i18n.t('keyboard.update_btb')}|"
        f"{i18n.t('keyboard.execute_script')}|{i18n.t('keyboard.back')}|{i18n.t('keyboard.go_back')}|{i18n.t('keyboard.ok')}|{i18n.t('keyboard.cancel_update')}|{i18n.t('keyboard.cancel')}|{i18n.t('keyboard.ok_s')}|{i18n.t('keyboard.great')})$"
    ),
    menu,
)

ENTRY_POINT_HANDLER = telegram.ext.CommandHandler(
    "start", menu, telegram.ext.Filters.chat(chat_id=eval(settings.CHAT_ID))
)

EDIT_COIN_LIST_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex("(.*?)"), edit_coin
)

EDIT_USER_CONFIG_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex("(.*?)"), edit_user_config
)

DELETE_DB_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex(
        f"^({i18n.t('keyboard.confirm')}|{i18n.t('keyboard.go_back')})$"
    ),
    delete_db,
)

UPDATE_TG_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex(
        f"^({i18n.t('keyboard.update')}|{i18n.t('keyboard.cancel_update')})$"
    ),
    update_tg_bot,
)

UPDATE_BTB_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex(
        f"^({i18n.t('keyboard.update')}|{i18n.t('keyboard.cancel_update')})$"
    ),
    update_btb,
)

PANIC_BUTTON_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex(
        f"^({i18n.t('keyboard.stop_sell')}|{i18n.t('keyboard.stop_cancel')}|{i18n.t('keyboard.stop_bot')}|{i18n.t('keyboard.go_back')})$"
    ),
    panic,
)

CUSTOM_SCRIPT_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex("(.*?)"), execute_custom_script
)

GRAPH_MENU_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex("(.*)"), graph_menu
)

CREATE_GRAPH_HANDLER = telegram.ext.MessageHandler(
    telegram.ext.Filters.regex("(.*)"), create_graph
)


FALLBACK_HANDLER = telegram.ext.CommandHandler("cancel", cancel)
