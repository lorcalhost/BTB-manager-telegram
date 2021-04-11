import logging
import sched
import time

(
    MENU,
    EDIT_COIN_LIST,
    EDIT_USER_CONFIG,
    DELETE_DB,
    UPDATE_TG,
    UPDATE_BTB,
    PANIC_BUTTON,
) = range(7)

BOUGHT, BUYING, SOLD, SELLING = range(4)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("btb_manager_telegram_logger")

scheduler = sched.scheduler(time.time, time.sleep)
