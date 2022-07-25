import configparser
import datetime as dt
import json
import os
import sqlite3
import subprocess

import i18n
import psutil
import yaml

from btb_manager_telegram import settings
from btb_manager_telegram.formating import escape_tg
from btb_manager_telegram.logging import logger
from btb_manager_telegram.schedule import scheduler


def setup_i18n(lang):
    i18n.set("locale", lang)
    i18n.set("fallback", "en")
    i18n.set("skip_locale_root_data", True)
    i18n.set("filename_format", "{locale}.{format}")
    i18n.load_path.append("./locales")


def get_db_cursor(fun):
    def _f_get_db_cursor(*args, **kwargs):
        db_file_path = os.path.join(settings.ROOT_PATH, "data/crypto_trading.db")
        if os.path.isfile(db_file_path):
            try:
                con = sqlite3.connect(db_file_path)
                cur = con.cursor()
            except Exception as e:
                logger.error(
                    f"Cannot connect to database, even if the file has been found."
                )
                return
            result = fun(*args, **kwargs, cur=cur)
            con.close()
            return result
        else:
            logger.error(f"The database file cannot be found at `{db_file_path}`")
            return

    return _f_get_db_cursor


def get_user_config(fun):
    def _f_user_config(*args, **kwargs):
        user_cfg_file_path = os.path.join(settings.ROOT_PATH, "user.cfg")
        if os.path.isfile(user_cfg_file_path):
            try:
                with open(user_cfg_file_path) as cfg:
                    config = configparser.ConfigParser()
                    config.read_file(cfg)
            except Exception as e:
                logger.error(f"Cannot read user.cfg, even if the file has been found.")
                return
            result = fun(*args, **kwargs, config=config)
            return result
        else:
            logger.error(f"The user.cfg file cannot be found at `{user_cfg_file_path}`")
            return

    return _f_user_config


def setup_telegram_constants():
    logger.info("Retrieving Telegram token and chat_id from apprise.yml file.")
    telegram_url = None
    yaml_file_path = os.path.join(settings.ROOT_PATH, "config/apprise.yml")
    if os.path.exists(yaml_file_path):
        with open(yaml_file_path) as f:
            try:
                parsed_urls = yaml.load(f, Loader=yaml.FullLoader)["urls"]
            except Exception as e:
                logger.error(
                    "Unable to correctly read apprise.yml file. Make sure it is correctly set up."
                )
                raise e
            for url in parsed_urls:
                if url.startswith("tgram"):
                    telegram_url = url.split("//")[1]
        if telegram_url is None:
            logger.critical(
                "The telegram configuration cannot be retrieved from apprise.yml, even if the file has been found."
            )
            exit(-1)
    else:
        logger.critical(
            "The apprise.yml file cannot be found, and the token and/or chat_id options are not set."
        )
        exit(-1)

    telegram_url = telegram_url.split("/")
    if len(telegram_url) != 2:
        logger.critical(
            "The telegram configuration cannot be retrieved from apprise.yml, even if the file has been found."
        )
        exit(-1)

    settings.TOKEN, settings.CHAT_ID = telegram_url
    logger.info(
        f"Successfully retrieved Telegram configuration. "
        f"The bot will only respond to user in the chat with chat_id {settings.CHAT_ID}"
    )


def retreive_btb_constants():
    logger.info("Retreiving binance tokens")
    btb_config_path = os.path.join(settings.ROOT_PATH, "user.cfg")
    if not os.path.isfile(btb_config_path):
        logger.critical(
            f"Binance Trade Bot config file cannot be found at `{btb_config_path}`"
        )
        exit(-1)
    btb_config = configparser.ConfigParser()
    btb_config.read(btb_config_path)
    settings.BINANCE_API_KEY = btb_config.get("binance_user_config", "api_key")
    settings.BINANCE_API_SECRET = btb_config.get(
        "binance_user_config", "api_secret_key"
    )
    settings.TLD = btb_config.get("binance_user_config", "tld")


def setup_coin_list():
    logger.info("Retreiving coin list")
    coin_list_path = os.path.join(settings.ROOT_PATH, "supported_coin_list")
    with open(coin_list_path, "r") as f:
        coin_list = [line.replace("\n", "").replace(" ", "") for line in f.readlines()]
    settings.COIN_LIST = [i for i in coin_list if i != ""]


def get_binance_trade_bot_process():
    name = "binance_trade_bot"
    is_root_path_absolute = os.path.isabs(settings.ROOT_PATH)
    bot_path = os.path.normpath(settings.ROOT_PATH)
    if not is_root_path_absolute:
        bot_path = os.path.normpath(os.path.join(os.getcwd(), settings.ROOT_PATH))

    for proc in psutil.process_iter():
        try:
            if (
                name in proc.name() or name in " ".join(proc.cmdline())
            ) and proc.cwd() == bot_path:
                return proc
        except psutil.AccessDenied:
            continue
        except psutil.ZombieProcess:
            continue


def find_and_kill_binance_trade_bot_process():
    try:
        binance_trade_bot_process = get_binance_trade_bot_process()
        binance_trade_bot_process.terminate()
        binance_trade_bot_process.wait()
    except Exception as e:
        logger.info(f"ERROR: {e}")


def kill_btb_manager_telegram_process():
    try:
        btb_manager_telegram_pid = os.getpid()
        btb_manager_telegram_process = psutil.Process(btb_manager_telegram_pid)
        btb_manager_telegram_process.kill()
        btb_manager_telegram_process.wait()
    except Exception as e:
        logger.info(f"ERROR: {e}")


def is_btb_bot_update_available():
    try:
        proc = subprocess.Popen(
            ["bash", "-c", "git remote update origin && git status -uno"],
            stdout=subprocess.PIPE,
        )
        output, _ = proc.communicate()
        re = "Your branch is behind" in str(output)
    except Exception as e:
        logger.error(e, exc_info=True)
        re = None
    return re


def is_tg_bot_update_available():
    result = subprocess.run(["git", "remote", "update", "origin"], capture_output=True)
    if result.returncode != 0:
        raise SystemError(result.stderr.decode())

    result = subprocess.run(
        ["git", "describe", "--abbrev=0", "--tags"], capture_output=True
    )
    if result.returncode != 0:
        raise SystemError(result.stderr.decode())
    current_version = result.stdout.decode().rstrip("\n")

    result = subprocess.run(
        ["git", "describe", "--abbrev=0", "--tags", "origin/main"], capture_output=True
    )
    if result.returncode != 0:
        raise SystemError(result.stderr.decode())
    remote_version = result.stdout.decode().rstrip("\n")

    re = current_version != remote_version
    return re, current_version, remote_version


def update_checker():
    logger.info("Checking for updates.")

    if settings.TG_UPDATE_BROADCASTED_BEFORE is False:
        to_update, cur_vers, rem_vers = is_tg_bot_update_available()
        if to_update:
            logger.info(
                f"BTB Manager Telegram update found. ({cur_vers} -> {rem_vers})"
            )
            message = f"{i18n.t('update.tgb.available', current_version=cur_vers, remote_version=rem_vers)}\n\n{i18n.t('update.tgb.instruction')}"
            print(message)
            settings.TG_UPDATE_BROADCASTED_BEFORE = True
            settings.CHAT.send_message(escape_tg(message), parse_mode="MarkdownV2")

    if settings.BTB_UPDATE_BROADCASTED_BEFORE is False:
        if is_btb_bot_update_available():
            logger.info("Binance Trade Bot update found.")
            message = (
                f"{i18n.t('update.btb.available')}\n\n"
                f"{i18n.t('update.btb.instruction')}"
            )
            settings.BTB_UPDATE_BROADCASTED_BEFORE = True
            settings.CHAT.send_message(escape_tg(message), parse_mode="MarkdownV2")


def get_custom_scripts_keyboard():
    logger.info("Getting list of custom scripts.")

    custom_scripts_path = "./config/custom_scripts.json"
    keyboard = []
    custom_script_exist = False
    message = i18n.t("script.no_script")

    if os.path.exists(custom_scripts_path):
        with open(custom_scripts_path) as f:
            scripts = json.load(f)
            for script_name in scripts:
                keyboard.append([script_name])

        if len(keyboard) >= 1:
            custom_script_exist = True
            message = i18n.t("script.select")
    else:
        logger.warning(
            "Unable to find custom_scripts.json file inside BTB-manager-telegram's config/ directory."
        )
        message = i18n.t("script.no_config")

    keyboard.append([i18n.t("keyboard.cancel")])
    return keyboard, custom_script_exist, message


def get_restart_file_name(old_pid):
    """
    returns the name of the file that has to be created
    by the new process to inform the old process of the btb to stop
    """
    return f"_restart_kill_{old_pid}"
