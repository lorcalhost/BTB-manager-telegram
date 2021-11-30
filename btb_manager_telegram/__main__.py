import argparse
import sys
import time
from subprocess import PIPE, run

import colorama
from telegram import Bot, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, Updater

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
    logger,
    scheduler,
    scheduler_thread,
    settings,
)
from btb_manager_telegram.buttons import start_bot
from btb_manager_telegram.report import make_snapshot
from btb_manager_telegram.utils import (
    escape_tg,
    i18n_format,
    retreive_btb_constants,
    setup_coin_list,
    setup_i18n,
    setup_root_path_constant,
    setup_telegram_constants,
    update_checker,
)


def pre_run_main() -> None:
    parser = argparse.ArgumentParser(
        description="Thanks for using Binance Trade Bot Manager Telegram. "
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
        help="(optional) Select a language. Available: en, ru, fr, de, nl, es",
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

    args = parser.parse_args()

    if args.docker:
        run_on_docker()
        exit(1)

    settings.ROOT_PATH = args.path
    settings.PYTHON_PATH = args.python_path
    settings.TOKEN = args.token
    settings.CHAT_ID = args.chat_id
    settings.LANG = args.language
    settings.START_TRADE_BOT = args.start_trade_bot
    settings.CURRENCY = args.currency
    settings.OER_KEY = args.oer_key
    settings.RAW_ARGS = " ".join(sys.argv[1:])

    if settings.CURRENCY not in ("USD", "EUR") and (
        settings.OER_KEY is None or settings.OER_KEY == ""
    ):
        raise ValueError(
            "If using another currency than USD or EUR, and openexchangerates API key is needed"
        )

    setup_i18n(settings.LANG)
    setup_root_path_constant()
    retreive_btb_constants()
    setup_coin_list()

    if settings.TOKEN is None or settings.CHAT_ID is None:
        setup_telegram_constants()

    settings.BOT = Bot(settings.TOKEN)
    settings.CHAT = settings.BOT.getChat(settings.CHAT_ID)

    scheduler.enter(1, 1, update_checker)
    scheduler.enter(1, 1, make_snapshot)
    scheduler_thread.start()

    return False


def main() -> None:

    from btb_manager_telegram import handlers

    """Start the bot."""

    # Start trade bot
    message_trade_bot = ""
    if settings.START_TRADE_BOT:
        trade_bot_status = start_bot()

        if trade_bot_status in (0, 1):
            message_trade_bot += i18n_format("welcome.bot_started")
        else:
            message_trade_bot += i18n_format("welcome.bot_not_started.base") + " "
            if trade_bot_status == 2:
                message_trade_bot += i18n_format("welcome.bot_not_started.bot_error")
            if trade_bot_status == 3:
                message_trade_bot += i18n_format("welcome.bot_not_started.bad_path")
            if trade_bot_status == 4:
                message_trade_bot += i18n_format("welcome.bot_not_started.no_python")
        message_trade_bot += "\n\n"

    # Create the Updater and pass it your token
    updater = Updater(settings.TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
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
    )
    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Welcome mat
    message = (
        f"{i18n_format('welcome.hello', name=settings.CHAT.first_name)}\n"
        f"{i18n_format('welcome.welcome')}\n\n"
        f"{i18n_format('welcome.developed_by')}\n"
        f"{i18n_format('welcome.project_link')}\n\n"
        f"{i18n_format('welcome.donation')}\n\n"
        f"{message_trade_bot}"
        f"{i18n_format('welcome.how_to_start')}"
    )
    keyboard = [["/start"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
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

    scheduler_thread.stop()
    scheduler_thread.join()

    logger.info("The telegram bot has stopped")


def run_on_docker() -> None:
    try:
        run("docker image inspect btbmt", shell=True, check=True, stdout=PIPE)
        run("docker run --rm -it btbmt", shell=True)

    except Exception as e:
        print(
            f"{colorama.Fore.RED}[-] Error: {e}{colorama.Fore.RESET}"
            f"{colorama.Fore.YELLOW}[*] Please run the docker_setup.py script "
            f"before running the bot in a container.{colorama.Fore.RESET}"
        )


if __name__ == "__main__":
    pre_run_main()
    main()
