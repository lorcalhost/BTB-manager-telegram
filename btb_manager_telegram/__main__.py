import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

import colorama
import i18n
import psutil
import telegram
import telegram.ext

from btb_manager_telegram import (
    CREATE_GRAPH,
    CUSTOM_SCRIPT,
    DELETE_DB,
    EDIT_COIN_LIST,
    EDIT_USER_CONFIG,
    GRAPH_MENU,
    MENU,
    PANIC_BUTTON,
    UPDATE_BTB,
    UPDATE_TG,
    settings,
)
from btb_manager_telegram.buttons import start_bot
from btb_manager_telegram.formating import escape_tg
from btb_manager_telegram.logging import logger, tg_error_handler
from btb_manager_telegram.report import make_snapshot, migrate_reports
from btb_manager_telegram.schedule import scheduler
from btb_manager_telegram.utils import (
    get_restart_file_name,
    retreive_btb_constants,
    setup_coin_list,
    setup_i18n,
    setup_telegram_constants,
    update_checker,
)


def pre_run_main() -> None:
    parser = argparse.ArgumentParser(
        description="Thanks for using Binance Trade telegram.Bot Manager Telegram. "
        'By default the program will use "../binance-trade-bot/" as binance-trade-bot installation path.'
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        help="(optional) binance-trade-bot installation path.",
        default="../binance-trade-bot/",
    )
    parser.add_argument(
        "-pp",
        "--python_path",
        type=str,
        help="(optional) Python binary to be used for the BTB. If unset, uses the same executable (and thus virtual env if any) than the telegram bot.",
        default=sys.executable,
    )
    parser.add_argument(
        "-t", "--token", type=str, help="(optional) Telegram bot token", default=None
    )
    parser.add_argument(
        "-l",
        "--language",
        type=str,
        help="(optional) Select a language. Available: en, ru, fr, de, nl, es, id",
        default="en",
    )
    parser.add_argument(
        "-s",
        "--start_trade_bot",
        action="store_true",
        help="Add this flag to start the trade bot when the telegram bot starts.",
    )
    parser.add_argument(
        "-c", "--chat_id", type=str, help="(optional) Telegram chat id", default=None
    )
    parser.add_argument(
        "-u",
        "--currency",
        type=str,
        help="(optional) The currency in which the reports are written",
        default="USD",
    )
    parser.add_argument(
        "-o",
        "--oer_key",
        type=str,
        help="openexchangerates.org api key. Mandatory if CURRENCY is not EUR or USD. Get yours here : https://openexchangerates.org/signup/free",
        default=None,
    )
    parser.add_argument(
        "-d",
        "--docker",
        action="store_true",
        help="(optional) Run the script in a docker container."
        "NOTE: Run the 'docker_setup.py' file before passing this flag.",
    )
    parser.add_argument(
        "--_remove_this_arg_auto_restart_old_pid", type=str, default=None
    )

    args = parser.parse_args()

    if args._remove_this_arg_auto_restart_old_pid is not None:
        old_pid = int(
            args._remove_this_arg_auto_restart_old_pid.lstrip("_remove_this_arg_")
        )
        logger.info(
            f"The new process says : Restart initied. Waiting for the old process with pid {old_pid} to terminate."
        )
        restart_filename = get_restart_file_name(old_pid)
        open(restart_filename, "w").close()
        while psutil.pid_exists(old_pid):
            time.sleep(0.1)
        os.remove(restart_filename)
        logger.info(f"The new process says : The old process has terminated. Starting.")

    if args.docker:
        run_on_docker()
        exit(1)

    settings.ROOT_PATH = os.path.join(args.path, "")
    settings.PYTHON_PATH = args.python_path
    settings.TOKEN = args.token
    settings.CHAT_ID = args.chat_id
    settings.LANG = args.language
    settings.START_TRADE_BOT = args.start_trade_bot
    settings.CURRENCY = args.currency
    settings.OER_KEY = args.oer_key
    settings.RAW_ARGS = [i for i in sys.argv[1:] if "_remove_this_arg_" not in i]

    if settings.CURRENCY not in ("USD", "EUR") and (
        settings.OER_KEY is None or settings.OER_KEY == ""
    ):
        raise ValueError(
            "If using another currency than USD or EUR, and openexchangerates API key is needed"
        )

    with open("btbmt.pid", "w") as f:
        f.write(str(os.getpid()))

    setup_i18n(settings.LANG)
    retreive_btb_constants()
    setup_coin_list()
    if settings.TOKEN is None or settings.CHAT_ID is None:
        setup_telegram_constants()
    settings.BOT = telegram.Bot(settings.TOKEN)
    settings.CHAT = settings.BOT.getChat(settings.CHAT_ID)

    migrate_reports()

    scheduler.exec_periodically(update_checker, dt.timedelta(days=7).total_seconds())
    scheduler.exec_periodically(make_snapshot, dt.timedelta(hours=1).total_seconds())
    scheduler.start()

    return False


def main() -> None:

    from btb_manager_telegram import handlers

    """Start the bot."""

    # Start trade bot
    message_trade_bot = ""
    if settings.START_TRADE_BOT:
        trade_bot_status = start_bot()

        if trade_bot_status in (0, 1):
            message_trade_bot += i18n.t("welcome.bot_started")
        else:
            message_trade_bot += i18n.t("welcome.bot_not_started.base") + " "
            if trade_bot_status == 2:
                message_trade_bot += i18n.t("welcome.bot_not_started.bot_error")
            if trade_bot_status == 3:
                message_trade_bot += i18n.t("welcome.bot_not_started.bad_path")
            if trade_bot_status == 4:
                message_trade_bot += i18n.t("welcome.bot_not_started.no_python")
        message_trade_bot += "\n\n"

    # Create the telegram.ext.Updater and pass it your token
    updater = telegram.ext.Updater(settings.TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    dispatcher.add_error_handler(tg_error_handler)

    conv_handler = telegram.ext.ConversationHandler(
        entry_points=[
            handlers.ENTRY_POINT_HANDLER,
        ],
        states={
            MENU: [handlers.MENU_HANDLER],
            EDIT_COIN_LIST: [handlers.EDIT_COIN_LIST_HANDLER],
            EDIT_USER_CONFIG: [handlers.EDIT_USER_CONFIG_HANDLER],
            DELETE_DB: [handlers.DELETE_DB_HANDLER],
            UPDATE_TG: [handlers.UPDATE_TG_HANDLER],
            UPDATE_BTB: [handlers.UPDATE_BTB_HANDLER],
            PANIC_BUTTON: [handlers.PANIC_BUTTON_HANDLER],
            CUSTOM_SCRIPT: [handlers.CUSTOM_SCRIPT_HANDLER],
            GRAPH_MENU: [handlers.GRAPH_MENU_HANDLER],
            CREATE_GRAPH: [handlers.CREATE_GRAPH_HANDLER],
        },
        fallbacks=[handlers.FALLBACK_HANDLER],
        per_user=True,
        allow_reentry=True,
    )
    dispatcher.add_handler(conv_handler)

    # Start the telegram.Bot
    updater.start_polling()

    # Welcome mat

    with open(".all-contributorsrc", "r") as f:
        contributors_data = json.load(f)
    contributors = ", ".join(
        [f"[{i['login']}]({i['profile']})" for i in contributors_data["contributors"]]
    )

    message = (
        f"{i18n.t('welcome.hello', name=settings.CHAT.first_name)}\n"
        f"{i18n.t('welcome.welcome')}\n\n"
        f"{i18n.t('welcome.developed_by', contributors=contributors)}\n"
        f"{i18n.t('welcome.project_link')}\n\n"
        f"{message_trade_bot}"
        f"{i18n.t('welcome.how_to_start')}"
    )

    keyboard = [["/start"]]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    settings.CHAT.send_message(
        escape_tg(message),
        reply_markup=reply_markup,
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
    )

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

    scheduler.stop()
    scheduler.join()

    try:
        os.remove("btbmt.pid")
    except FileNotFoundError:
        pass

    logger.info("The telegram bot has stopped")


def run_on_docker() -> None:
    try:
        subprocess.run(
            "docker image inspect btbmt", shell=True, check=True, stdout=subprocess.PIPE
        )
        subprocess.run("docker run --rm -it btbmt", shell=True)

    except Exception as e:
        print(
            f"{colorama.Fore.RED}[-] Error: {e}{colorama.Fore.RESET}"
            f"{colorama.Fore.YELLOW}[*] Please run the docker_setup.py script "
            f"before running the bot in a container.{colorama.Fore.RESET}"
        )


if __name__ == "__main__":
    pre_run_main()
    main()
