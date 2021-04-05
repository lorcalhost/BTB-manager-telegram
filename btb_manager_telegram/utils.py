import psutil
import yaml

from btb_manager_telegram import logger, settings


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


def setup_telegram_constants():
    logger.info("Retrieving Telegram token and user_id from apprise.yml file.")
    telegram_url = None
    yaml_file_path = f"{settings.ROOT_PATH}config/apprise.yml"
    with open(yaml_file_path) as f:
        parsed_urls = yaml.load(f, Loader=yaml.FullLoader)["urls"]
        for url in parsed_urls:
            if url.startswith("tgram"):
                telegram_url = url.split("//")[1]
    if not telegram_url:
        logger.error(
            "ERROR: No telegram configuration was found in your apprise.yml file.\nAborting."
        )
        exit(-1)
    try:
        settings.TOKEN = telegram_url.split("/")[0]
        settings.USER_ID = telegram_url.split("/")[1]
        logger.info(
            f"Successfully retrieved Telegram configuration. "
            f"The bot will only respond to user with user_id {settings.USER_ID}"
        )
    except:
        logger.error(
            "ERROR: No user_id has been set in the yaml configuration, anyone would be able to control your bot.\n"
            "Aborting."
        )
        exit(-1)


def text_4096_cutter(m_list):
    message = [""]
    index = 0
    for m in m_list:
        if len(message[index]) + len(m) <= 4096:
            message[index] += m
        else:
            message.append(m)
            index += 1
    return message


def find_process():
    for proc in psutil.process_iter():
        if "binance_trade_bot" in proc.name() or "binance_trade_bot" in " ".join(
            proc.cmdline()
        ):
            return True
    return False
