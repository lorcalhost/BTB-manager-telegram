import logging
import sys
import traceback

from telegram.utils.helpers import escape_markdown

from btb_manager_telegram import settings
from btb_manager_telegram.formating import escape_tg, telegram_text_truncator


class LoggerHandler(logging.Handler):
    def __init__(self):
        """
        Logging Handler which forwards warning, critical and error
        logs to the telegram conversation
        """
        super().__init__()

    def emit(self, record):
        if record.levelno >= logging.WARNING:  # warning, critical or error
            emoji = ""
        if record.levelno == logging.WARNING:
            emoji = "⚠️"
        elif record.levelno == logging.ERROR:
            emoji = "❌"
        elif record.levelno == logging.CRITICAL:
            emoji = "☠️"
        else:
            return
        message = f"{emoji} {record.levelname.title()} : {record.msg}"
        message_list = telegram_text_truncator(message)
        for msg in message_list:
            try:
                settings.CHAT.send_message(
                    escape_tg(message, exclude_parenthesis=True),
                    parse_mode="MarkdownV2",
                )
            except Exception as e:
                # do not use logging.error here! it will end badly.
                print(f"The latest error cannot be sent to telegram, reason : {e}")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("btb_manager_telegram")
logger.addHandler(LoggerHandler())


def if_exception_log(message=None, level=logging.ERROR, raise_error=True):
    """
    Decorator to use on functions we want to handle errors.
    We can simply log them, optionally include the
    traceback in the log message by inserting %{e},
    and eventually raised the caught error afterwards
    """

    def _f_if_exception_log(fun):
        def _exec_if_exception_fun(*args, **kwargs):
            result = None
            try:
                result = fun(*args, **kwargs)
            except Exception as e:
                if message is not None:
                    logger.log(
                        level,
                        message.replace(
                            "%{e}",
                            f"\n```\n{''.join(traceback.format_exception(*sys.exc_info()))}\n```\n",
                        ).rstrip("\n"),
                    )
                raise e
            return result

        return _exec_if_exception_fun

    return _f_if_exception_log


def tg_error_handler(update, context):
    """
    Error handler for the telegram conversation handler
    """
    error = sys.exc_info()
    if None in error:
        error = context.error
    else:
        error = "".join(traceback.format_exception(*error))
    message = f"```\n{error}\n```"
    settings.CHAT.send_message(
        escape_tg(message, exclude_parenthesis=True), parse_mode="MarkdownV2"
    )
