from telegram import ReplyKeyboardMarkup

import i18n

menu = ReplyKeyboardMarkup(
    [
        [i18n_format("keyboard.current_value"), i18n_format("keyboard.progress")],
        [i18n_format("keyboard.current_ratios"), i18n_format("keyboard.next_coin")],
        [i18n_format("keyboard.check_status"), i18n_format("keyboard.trade_history")],
        [i18n_format("keyboard.coin_forecast"), i18n_format("keyboard.bot_stats")],
        [i18n_format("keyboard.graph")],
        [i18n_format("keyboard.maintenance"), i18n_format("keyboard.configurations")],
    ],
    resize_keyboard=True,
)

config = ReplyKeyboardMarkup(
    [
        [i18n.t("keyboard.start"), i18n.t("keyboard.stop")],
        [i18n.t("keyboard.read_logs"), i18n.t("keyboard.delete_db")],
        [i18n.t("keyboard.edit_cfg"), i18n.t("keyboard.edit_coin_list")],
        [i18n.t("keyboard.export_db"), i18n.t("keyboard.back")],
    ],
    resize_keyboard=True,
)

maintenance = ReplyKeyboardMarkup(
    [
        [i18n.t("keyboard.update_tgb")],
        [i18n.t("keyboard.update_btb")],
        [i18n.t("keyboard.execute_script")],
        [i18n.t("keyboard.back")],
    ],
    resize_keyboard=True,
)
