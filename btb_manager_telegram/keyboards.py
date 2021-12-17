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

config = ReplyKeyboardMarkup(
    [
        [i18n_format("keyboard.start"), i18n_format("keyboard.stop")],
        [i18n_format("keyboard.read_logs"), i18n_format("keyboard.delete_db")],
        [i18n_format("keyboard.edit_cfg"), i18n_format("keyboard.edit_coin_list")],
        [i18n_format("keyboard.export_db"), i18n_format("keyboard.back")],
    ],
    resize_keyboard=True,
)

maintenance = ReplyKeyboardMarkup(
    [
        [i18n_format("keyboard.update_tgb")],
        [i18n_format("keyboard.update_btb")],
        [i18n_format("keyboard.execute_script")],
        [i18n_format("keyboard.back")],
    ],
    resize_keyboard=True,
)
