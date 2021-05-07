import json

from btb_manager_telegram import logger


def json_print(obj):
    # Create  formatted JSON string from a Python dictionary
    text = json.dumps(obj, sort_keys=True, indent=4)
    logger.debug(text)
