import os
import subprocess

import psutil
import yaml
from telegram import Bot

from btb_manager_telegram import logger, scheduler, settings


def setup_root_path_constant():
    if settings.ROOT_PATH is None:
        logger.info("No root_path was specified. Aborting.")
        exit(-1)
    else:
        settings.ROOT_PATH = os.path.join(settings.ROOT_PATH, "")


def setup_telegram_constants():
    logger.info("Retrieving Telegram token and user_id from apprise.yml file.")
    telegram_url = None
    yaml_file_path = f"{settings.ROOT_PATH}config/apprise.yml"
    if os.path.exists(yaml_file_path):
        with open(yaml_file_path) as f:
            try:
                parsed_urls = yaml.load(f, Loader=yaml.FullLoader)["urls"]
            except Exception:
                logger.error("Unable to correctly read apprise.yml file. Make sure it is correctly set up. Aborting.")
                exit(-1)
            for url in parsed_urls:
                if url.startswith("tgram"):
                    telegram_url = url.split("//")[1]
        if not telegram_url:
            logger.error(
                "No telegram configuration was found in your apprise.yml file. Aborting."
            )
            exit(-1)
    else:
        logger.error(
            f'Unable to find apprise.yml file at "{yaml_file_path}". Aborting.'
        )
        exit(-1)
    try:
        settings.TOKEN = telegram_url.split("/")[0]
        settings.USER_ID = telegram_url.split("/")[1]
        logger.info(
            f"Successfully retrieved Telegram configuration. "
            f"The bot will only respond to user with user_id {settings.USER_ID}"
        )
    except Exception:
        logger.error(
            "No user_id has been set in the yaml configuration, anyone would be able to control your bot. Aborting."
        )
        exit(-1)


def text_4096_cutter(m_list):
    message = [""]
    index = 0
    for mes in m_list:
        if len(message[index]) + len(mes) <= 4096:
            message[index] += mes
        else:
            message.append(mes)
            index += 1
    return message


def find_process():
    return any(
        "binance_trade_bot" in proc.name()
        or "binance_trade_bot" in " ".join(proc.cmdline())
        for proc in psutil.process_iter()
    )


def find_and_kill_process():
    try:
        for proc in psutil.process_iter():
            if "binance_trade_bot" in proc.name() or "binance_trade_bot" in " ".join(
                proc.cmdline()
            ):
                proc.terminate()
                proc.wait()
    except Exception as e:
        logger.info(f"ERROR: {e}")


def is_tg_bot_update_available():
    try:
        proc = subprocess.Popen(
            ["bash", "-c", "git remote update && git status -uno"],
            stdout=subprocess.PIPE,
        )
        output, _ = proc.communicate()
        re = "Your branch is behind" in str(output)
    except Exception:
        re = None
    return re


def is_btb_bot_update_available():
    try:
        proc = subprocess.Popen(
            [
                "bash",
                "-c",
                f"cd {settings.ROOT_PATH} && git remote update && git status -uno",
            ],
            stdout=subprocess.PIPE,
        )
        output, _ = proc.communicate()
        re = "Your branch is behind" in str(output)
    except Exception:
        re = None
    return re


def update_checker():
    logger.info("Checking for updates.")

    if settings.TG_UPDATE_BROADCASTED_BEFORE is False:
        if is_tg_bot_update_available():
            logger.info("BTB Manager Telegram update found.")

            message = (
                "⚠ An update for _BTB Manager Telegram_ is available\.\n\n"
                "Please update by going to *🛠 Maintenance* and pressing the *Update Telegram Bot* button\."
            )
            settings.TG_UPDATE_BROADCASTED_BEFORE = True
            bot = Bot(settings.TOKEN)
            bot.send_message(settings.USER_ID, message, parse_mode="MarkdownV2")
            scheduler.enter(
                60 * 60 * 12,
                1,
                update_reminder,
                ("_*Reminder*_:\n\n" + message,),
            )

    if settings.BTB_UPDATE_BROADCASTED_BEFORE is False:
        if is_btb_bot_update_available():
            logger.info("Binance Trade Bot update found.")

            message = (
                "⚠ An update for _Binance Trade Bot_ is available\.\n\n"
                "Please update by going to *🛠 Maintenance* and pressing the *Update Binance Trade Bot* button\."
            )
            settings.BTB_UPDATE_BROADCASTED_BEFORE = True
            bot = Bot(settings.TOKEN)
            bot.send_message(settings.USER_ID, message, parse_mode="MarkdownV2")
            scheduler.enter(
                60 * 60 * 12,
                1,
                update_reminder,
                ("_*Reminder*_:\n\n" + message,),
            )

    if (
        settings.TG_UPDATE_BROADCASTED_BEFORE is False
        or settings.BTB_UPDATE_BROADCASTED_BEFORE is False
    ):
        scheduler.enter(
            60 * 60,
            1,
            update_checker,
        )


def update_reminder(self, message):
    logger.info(f"Reminding user: {message}")

    bot = Bot(settings.TOKEN)
    bot.send_message(settings.USER_ID, message, parse_mode="MarkdownV2")
    scheduler.enter(
        60 * 60 * 12,
        1,
        update_reminder,
    )
