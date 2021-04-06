from telegram import Bot

from btb_manager_telegram import logger, settings
from btb_manager_telegram.utils import (
    is_btb_bot_update_available,
    is_tg_bot_update_available,
)

TG_UPDATE_BROADCASTED_BEFORE = None
BTB_UPDATE_BROADCASTED_BEFORE = None
SCHEDULER = None


def update_checker():
    logger.info("Checking for updates.")

    if TG_UPDATE_BROADCASTED_BEFORE is False:
        if is_tg_bot_update_available():
            logger.info("BTB Manager Telegram update found.")

            message = "⚠ An update for _BTB Manager Telegram_ is available\.\n\nPlease update by going to *🛠 Maintenance* and pressing the *Update Telegram Bot* button\."
            TG_UPDATE_BROADCASTED_BEFORE = True
            bot = Bot(settings.TOKEN)
            bot.send_message(settings.USER_ID, message, parse_mode="MarkdownV2")
            SCHEDULER.enter(
                60 * 60 * 12,
                1,
                update_reminder,
                ("_*Reminder*_:\n\n" + message,),
            )

    if BTB_UPDATE_BROADCASTED_BEFORE is False:
        if is_btb_bot_update_available():
            logger.info("Binance Trade Bot update found.")

            message = "⚠ An update for _Binance Trade Bot_ is available\.\n\nPlease update by going to *🛠 Maintenance* and pressing the *Update Binance Trade Bot* button\."
            BTB_UPDATE_BROADCASTED_BEFORE = True
            bot = Bot(settings.TOKEN)
            bot.send_message(settings.USER_ID, message, parse_mode="MarkdownV2")
            SCHEDULER.enter(
                60 * 60 * 12,
                1,
                update_reminder,
                ("_*Reminder*_:\n\n" + message,),
            )

    if TG_UPDATE_BROADCASTED_BEFORE is False or BTB_UPDATE_BROADCASTED_BEFORE is False:
        SCHEDULER.enter(
            60 * 60,
            1,
            update_checker,
        )


def update_reminder(self, message):
    logger.info(f"Reminding user: {message}")

    bot = Bot(settings.TOKEN)
    bot.send_message(settings.USER_ID, message, parse_mode="MarkdownV2")
    SCHEDULER.enter(
        60 * 60 * 12,
        1,
        update_reminder,
    )
