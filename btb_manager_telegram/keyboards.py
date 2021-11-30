from telegram import ReplyKeyboardMarkup

from btb_manager_telegram.utils import i18n_format

menu = ReplyKeyboardMarkup(
    [
        [i18n_format("keyboard.current_value"), i18n_format("keyboard.progress")],
        [i18n_format("keyboard.current_ratios"), i18n_format("keyboard.next_coin")],
        [i18n_format("keyboard.check_status"), i18n_format("keyboard.trade_history")],
        [i18n_format("keyboard.graph")],
        [i18n_format("keyboard.maintenance"), i18n_format("keyboard.configurations")],
    ],
    resize_keyboard=True,
)
