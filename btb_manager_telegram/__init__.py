import threading
import time

from btb_manager_telegram.logging import logger, logger_handler

(
    MENU,
    EDIT_COIN_LIST,
    EDIT_USER_CONFIG,
    DELETE_DB,
    UPDATE_TG,
    UPDATE_BTB,
    PANIC_BUTTON,
    CUSTOM_SCRIPT,
    GRAPH_MENU,
    CREATE_GRAPH,
) = range(10)

BOUGHT, BUYING, SOLD, SELLING = range(4)
