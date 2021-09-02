import argparse
import sys
import time
from subprocess import PIPE, run

import colorama
from telegram.ext import ConversationHandler, Updater

from btb_manager_telegram import (
    CUSTOM_SCRIPT,
    DELETE_DB,
    EDIT_COIN_LIST,
    EDIT_USER_CONFIG,
    MENU,
    PANIC_BUTTON,
    UPDATE_BTB,
    UPDATE_TG,
    scheduler,
    settings,
)
from btb_manager_telegram.utils import (
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
        help="(optional) Select a language. Available: 'en'",
        default="en",
    )
    parser.add_argument(
        "-c", "--chat_id", type=str, help="(optional) Telegram chat id", default=None
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
    settings.RAW_ARGS = " ".join(sys.argv[1:])

    setup_i18n(settings.LANG)
    setup_root_path_constant()

    if settings.TOKEN is None or settings.CHAT_ID is None:
        setup_telegram_constants()

    # Setup update notifications scheduler
    scheduler.enter(1, 1, update_checker)
    time.sleep(1)
    scheduler.run(blocking=False)

    return False


def main() -> None:
    from btb_manager_telegram import handlers

    """Start the bot."""
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
        },
        fallbacks=[handlers.FALLBACK_HANDLER],
        per_user=True,
    )
    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


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
