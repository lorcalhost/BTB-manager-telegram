import argparse
import sched
import time

from telegram.ext import ConversationHandler, Updater

from btb_manager_telegram import (
    DELETE_DB,
    EDIT_COIN_LIST,
    EDIT_USER_CONFIG,
    MENU,
    UPDATE_BTB,
    UPDATE_TG,
    settings,
)
from btb_manager_telegram import update_notifications as notify
from btb_manager_telegram.utils import (
    setup_root_path_constant,
    setup_telegram_constants,
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
    settings.ROOT_PATH = args.path
    settings.TOKEN = args.token
    settings.USER_ID = args.user_id

    setup_root_path_constant()

    if settings.TOKEN is None or settings.USER_ID is None:
        setup_telegram_constants()

    notify.TG_UPDATE_BROADCASTED_BEFORE = False
    notify.BTB_UPDATE_BROADCASTED_BEFORE = False
    notify.SCHEDULER = sched.scheduler(time.time, time.sleep)
    notify.SCHEDULER.enter(1, 1, notify.update_checker)
    time.sleep(1)
    notify.SCHEDULER.run(blocking=False)


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


if __name__ == "__main__":
    pre_run_main()
    main()
